from django.shortcuts import render
from manager.models import *
from django import http
from django.views import View
import json
import pytz
from django.db.models import Max, Q, Count, Min
from django.db import transaction
from django.core import serializers
from manager.param import *
from datetime import datetime
"""
获取所有订单 GET api/kitchen
获取某个订单 GET api/kitchen/{pk}
通过状态查询菜品  POST api/kitchen/dish     parms:dish_status  
通过工号查询菜品  POST api/kitchen/workstation     parms:station_id
"""

#查看所有订单+菜的基本信息
class kitchenView(View):
    def get(self, request):
        orders = order_detail.objects.all()
        order_list = []
        for order in orders:
            order = {
                'order_id':order.order_id.pk,
                'order_type':all_order_log.objects.get(order_id = order.order_id.pk).order_type,
                'dish_id': order.dish_id,
                'dish_name':dish.objects.get(dish_id = order.dish_id).name,
                'count':order.count,
                'create_time':order.create_time.strftime('%Y%m%d %H:%M:%S'),
                'dish_status':order.dish_status,
                'station_id':order.station_id,
                'waiting_list':order.waiting_list
            }
            order_list.append(order)
        #print(order_list)
        return http.JsonResponse({"dishes":order_list})

# 查看菜品完成情况
class KitchenDish(View):
    ## 总查看各类不同状态的菜的信息
    def get(self, request):
        dishes = []
        all_dish_number = len(order_detail.objects.all())
        all_dish_id = len(all_order_log.objects.all())
        print(all_dish_number)
        # 总共有5种状态的菜
        for did in range(5):
            dish_status_count = {"dish_status": did, "count":0, "count_percent":0, "count_id":0}
            if all_dish_number != 0:
                dish_status_count['count'] = len(order_detail.objects.filter(dish_status = did))
                dish_status_count['count_percent'] = dish_status_count['count']/all_dish_number
                dish_status_count['count_id'] = len(order_detail.objects.filter(dish_status = did).values('order_id').distinct())/all_dish_id
            dishes.append(dish_status_count)
        return http.JsonResponse({"dishes":dishes})


    def post(self, request):
        print('查看菜品完成情况')  # dish_status
        dict_data = json.loads(request.body, strict = False)
        print(dict_data)
        orders = order_detail.objects.filter(dish_status = dict_data['dish_status'])
        dishes_list = []
        for order in orders:
            order = {
                'order_id': order.order_id.pk,
                'order_type': all_order_log.objects.get(order_id=order.order_id.pk).order_type,
                'dish_id': order.dish_id,
                'dish_name': dish.objects.get(dish_id = order.dish_id).name,
                'count': order.count,
                'create_time': order.create_time.strftime('%Y%m%d %H:%M:%S'),
                'dish_status': order.dish_status,
                'station_id': order.station_id,
                'waiting_list':order.waiting_list
            }
            dishes_list.append(order)
        return http.JsonResponse({"dishes":dishes_list}, safe=False)

class kitchendetailView(View):
    # 查看全部订单的统计信息
    def get(self, request):
        dishes = []
        order_max = all_order_log.objects.all().last().order_id
        for i in range(order_max):
            if len(order_detail.objects.filter(order_id = i + 1)) > 0:
            # 只有当这个订单真实存在的时候且完成下单
                order_info = {"order_id": i + 1, "order_type":all_order_log.objects.get(order_id = i + 1).order_type}
                print(order_info)
                order_info['create_time'] = order_detail.objects.filter(order_id = i + 1).first().create_time.strftime('%Y%m%d %H:%M:%S')
                order_info['count'] = len(order_detail.objects.filter(order_id = i + 1))
                ## 计算完成率
                if order_info['count'] != 0:
                    order_info['finish_percent'] = (len(order_detail.objects.filter(order_id = i + 1, dish_status = 2)) + len(order_detail.objects.filter(order_id = i + 1, dish_status = 3)))/order_info['count']
                else:
                    order_info['finish_percent'] = 0
                dishes.append(order_info)
        #print(dishes)
        return http.JsonResponse({"dishes":dishes})

    # 查看某一订单的详情
    def post(self, request):
        try:
            dict_data = json.loads(request.body, strict = False)
            all_orders = order_detail.objects.filter(order_id = dict_data['order_id'])
            all_order = []
            for order in all_orders:
                order = {
                    'order_id': order.order_id.pk,
                    'order_type': all_order_log.objects.get(order_id=order.order_id.pk).order_type,
                    'dish_id': order.dish_id,
                    'dish_name': dish.objects.get(dish_id = order.dish_id).name,
                    'count': order.count,
                    'create_time': order.create_time.strftime('%Y%m%d %H:%M:%S'),
                    'dish_status': order.dish_status,
                    'station_id':order.station_id,
                    'waiting_list': order.waiting_list
                }
                all_order.append(order)
            return http.JsonResponse({"dishes":all_order}, safe=False)
        except Exception as e:
            return http.HttpResponse(status = 404)


class KitchenWorkstation(View):
    ## 获取目前工位的所有信息
    def get(self, request):
        dishes = []
        #目前所有的station_id:
        for sid in range(1, all_number + 1):
            sid_dict = {"station_id":sid, "current_status":0, "workload":0, "waiting_number":0}
            ## 统计信息
            ### 判断现在是忙还是闲:
            if len(order_detail.objects.filter(station_id = sid, dish_status = 4)) == 1:
                sid_dict['current_status'] = 1
                sid_dict['waiting_number'] = order_detail.objects.filter(station_id = sid).aggregate(Max('waiting_list'))['waiting_list__max']
            ### 计算工作量
            first_time = order_detail.objects.all().aggregate(Min('create_time'))['create_time__min']
            #print(first_time)

            ## 防止是空值
            if first_time is None:
                dishes.append(sid_dict)
                continue
            else:
                sys_start_time = first_time
            #### 计算过去的总时间(从最早的订单开始, 计算秒数)
            
            all_past_time = (datetime.now() - sys_start_time).total_seconds()
            
            #### 计算该工位目前的工作时间
            #### 筛选出目前所有的完餐或正在做的菜
            all_work_time = 0
            sid_info = order_detail.objects.filter(station_id = sid).exclude(dish_status = 0).exclude(dish_status = 1).exclude(dish_status = 3)
            for sid_detail in sid_info:
                # 正在做
                if sid_detail.dish_status == 4:
                    all_work_time += (datetime.now() - sid_detail.start_time).total_seconds()
                # 已经做完
                else:
                    #print(all_past_time, all_work_time, sid_detail.station_id, sid_detail.order_id, sid_detail.dish_id)
                    all_work_time += (sid_detail.finish_time - sid_detail.start_time).total_seconds()
            sid_dict['workload'] = all_work_time/all_past_time
            dishes.append(sid_dict)
            #print(sid_dict['workload'])
        return http.JsonResponse({"dishes":dishes})
            
    ## 查看某一工位的具体信息
    def post(self, request):
        try:
            dict_data = json.loads(request.body, strict = False)
            print(dict_data)
            orders = order_detail.objects.filter(station_id = dict_data['station_id'])
            ##去除已经完成/废弃的菜, 并按照WL进行排序
            orders = orders.exclude(dish_status = 2)
            orders = orders.exclude(dish_status = 3).order_by('waiting_list')
            dishes_list = []
            for order in orders:
                order = {
                    'order_id': order.order_id.pk,
                    'order_type': all_order_log.objects.get(order_id=order.order_id.pk).order_type,
                    'dish_id': order.dish_id,
                    'dish_name': dish.objects.get(dish_id = order.dish_id).name,
                    'count': order.count,
                    'create_time': order.create_time.strftime('%Y%m%d %H:%M:%S'),
                    "station_id":order.station_id,
                    'dish_status': order.dish_status,
                    'waiting_list': order.waiting_list,
                }
                dishes_list.append(order)
            return http.JsonResponse({"dish_station":dishes_list}, safe=False)
        except:
            return http.HttpResponse(status = 404)

# 查看某一订单某菜的详情
class kitchendetail(View):
    def post(self, request):
        try:
            dict_data = json.loads(request.body, strict = False)
            print(dict_data)
            order_dish_info = order_detail.objects.get(order_id = dict_data['order_id'], dish_id = dict_data['dish_id'])
            print(order_dish_info)
            dish_info ={
                "order_type":all_order_log.objects.get(order_id = dict_data['order_id']).order_type,
                "order_id":dict_data['order_id'],
                "dish_id":order_dish_info.dish_id,
                "count":order_dish_info.count,
                "create_time":order_dish_info.create_time.strftime('%Y%m%d %H:%M:%S'),
                "dish_status":order_dish_info.dish_status,
                #"start_time":order_dish_info.start_time.strftime('%Y%m%d %H:%M:%S'),
                "station_id":order_dish_info.station_id,
                "waiting_list":order_dish_info.waiting_list,
                "ingd_cost":order_dish_info.ingd_cost
            }
            print(dish_info)
            return http.JsonResponse(dish_info, safe=False)
        except Exception as e:
            print(Exception)
            return http.HttpResponse(status = 404)

# 模糊查询的接口   
def search(request):
    select_id = None
    select_dishes = order_detail.objects.all()
    if request.body == b'':
        pass
    else:
        dict_data = json.loads(request.body, strict = False)
        
        ## 搜寻到最终需要满足的要求
        
        #print(dict_data)
        for dict_key in dict_data.keys():
            if dict_data[dict_key] is not None and dict_data[dict_key]!= '':
                print(dict_data[dict_key], dict_key)
                if dict_key == 'order_id':
                    select_dishes = select_dishes.filter(order_id = dict_data[dict_key])
                elif dict_key == 'dish_id':
                    select_dishes = select_dishes.filter(dish_id = dict_data[dict_key])
                elif dict_key == 'count':
                    select_dishes = select_dishes.filter(count = dict_data[dict_key])
                elif dict_key == 'dish_status':
                    select_dishes = select_dishes.filter(dish_status = dict_data[dict_key])
                elif dict_key == 'station_id':
                    select_dishes = select_dishes.filter(station_id = dict_data[dict_key])
                elif dict_key == 'waiting_list':
                    select_dishes = select_dishes.filter(waiting_list = dict_data[dict_key])
                elif dict_key == 'dish_name':
                    select_id = dish.objects.filter(name__contains = dict_data[dict_key]).values("dish_id")
                    select_id = [sid['dish_id'] for sid in select_id]


    # 搜寻完成
    Finish_list = []
    for order in select_dishes:
        if select_id is None or order.dish_id in select_id:
            order = {
                'order_id': order.order_id.pk,
                'dish_id':order.dish_id,
                'dish_name': dish.objects.get(dish_id = order.dish_id).name,
                'count': order.count,
                'create_time': order.create_time.strftime('%Y%m%d %H:%M:%S'),
                'dish_status': order.dish_status,
                'station_id': order.station_id,
                'waiting_list': order.waiting_list,
            }
            Finish_list.append(order)
    print(Finish_list)
    return http.JsonResponse({"dishes": Finish_list}, safe=False)






