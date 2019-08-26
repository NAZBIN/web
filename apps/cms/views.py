from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.views.generic import View
from django.views.decorators.http import require_POST,require_GET
from apps.news.models import NewsCategory,News,Banner
from utils import restful
from .forms import EditNewsCategoryForm,WriteNewsForm,AddBannerForm,UpdateBannerForm,EditNewsForm
import os
from datetime import datetime
from django.core.paginator import Paginator
from urllib import parse
from django.utils.timezone import make_aware
from django.conf import settings
import qiniu
from apps.news.serializers import BannerSerializer

#cms首页
@staff_member_required(login_url='index')
def index(request):
    return render(request,'cms/index.html')

class NewsListView(View):
    def get(self,request):
        # request.GET：获取出来的所有数据，都是字符串类型
        page = int(request.GET.get('p',1))#拿到page
        start = request.GET.get('start')
        end = request.GET.get('end')
        title = request.GET.get('title')
        # request.GET.get(参数,默认值)
        # 这个默认值是只有这个参数没有传递的时候才会使用
        # 如果传递了，但是是一个空的字符串，那么也不会使用默认值
        category_id = int(request.GET.get('category',0) or 0) #如果没有category,那让它的默认值为0,0表示所有分类
                                        #第一个0是当没有传递category的时候才会让它为0
        newses = News.objects.select_related('category', 'author')
        #判断用户是否选择了开始时间和结束时间， 针对性的进行过滤
        if start or end:
            if start:
                start_date = datetime.strptime(start,'%Y/%m/%d')
            else:
                start_date = datetime(year=2019,month=8,day=1)
            if end:
                end_date = datetime.strptime(end,'%Y/%m/%d')
            else:
                end_date = datetime.today()    #make_aware会将指定的时间转换为TIME_ZONE中指定时区的时间
            newses = newses.filter(pub_time__range=(make_aware(start_date),make_aware(end_date)))
        #判断标题
        if title:
            newses = newses.filter(title__icontains=title) #icontains大小写不敏感
        #判断分类
        if category_id:
            newses = newses.filter(category=category_id)

        paginator = Paginator(newses,2)#类的对象,传入可遍历的对象，和一页当中要显示的数据数量
        page_obj = paginator.page(page) #返回当前页的Page对象，代表当前这一页

        context_data = self.get_pagination_data(paginator,page_obj)

        context = {
            'categories': NewsCategory.objects.all(),
            'newses': page_obj.object_list,#object_list需要渲染的数据 如果用news的话会把所有新闻数据都渲染出来
            'page_obj': page_obj,
            'paginator': paginator,
            'start': start,
            'end': end,
            'title': title,
            'category_id': category_id,
            'url_query': '&'+parse.urlencode({ #url查询的参数
                'start': start or '',
                'end': end or '',
                'title': title or '',
                'category': category_id or ''
            })
        }

        print('='*30)
        print(category_id)
        print('='*30)

        context.update(context_data)

        return render(request, 'cms/news_list.html', context=context)


    def get_pagination_data(self,paginator,page_obj,around_count=2):#around_cout左右两边需要展示的页码
        current_page = page_obj.number
        num_pages = paginator.num_pages

        left_has_more = False
        right_has_more = False

        if current_page <= around_count + 2:
            left_pages = range(1,current_page)
        else:
            left_has_more = True
            left_pages = range(current_page-around_count,current_page)

        if current_page >= num_pages - around_count - 1:
            right_pages = range(current_page+1,num_pages+1)
        else:
            right_has_more = True
            right_pages = range(current_page+1,current_page+around_count+1)

        return {
            # left_pages：代表的是当前这页的左边的页的页码
            'left_pages': left_pages,
            # right_pages：代表的是当前这页的右边的页的页码
            'right_pages': right_pages,
            'current_page': current_page,
            'left_has_more': left_has_more,
            'right_has_more': right_has_more,
            'num_pages': num_pages
        }
# def news_list(request):
#     context = {
#         'categories':NewsCategory.objects.all(),
#         'newses':News.objects.select_related('category','author').all()
#     }
#     return render(request,'cms/news_list.html',context=context)


class WriteNewsView(View):
    def get(self,request,*args,**kwargs):
        categories = NewsCategory.objects.all()
        context = {
            'categories': categories
        }
        return render(request,'cms/write_news.html',context=context)
    def post(self,request):
        form = WriteNewsForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data.get('title')
            desc = form.cleaned_data.get('desc')
            thumbnail = form.cleaned_data.get('thumbnail')
            content = form.cleaned_data.get('content')
            category_id = form.cleaned_data.get('category')
            category = NewsCategory.objects.get(pk=category_id)
            News.objects.create(title=title,desc=desc,thumbnail=thumbnail,content=content,category=category,author=request.user)
            return restful.ok()
        else:
            return restful.paramserror(message=form.get_errors())

class EditNewsView(View):
    def get(self,request):
        news_id = request.GET.get('news_id')
        news = News.objects.select_related('category').get(pk=news_id)
        context = {
            'news': news,
            'categories': NewsCategory.objects.all()
        }
        return render(request,'cms/write_news.html',context=context)

    def post(self,request):
        form = EditNewsForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data.get('title')
            desc = form.cleaned_data.get('desc')
            thumbnail = form.cleaned_data.get('thumbnail')
            content = form.cleaned_data.get('content')
            category_id = form.cleaned_data.get('category')
            pk = form.cleaned_data.get("pk")
            category = NewsCategory.objects.get(pk=category_id)
            News.objects.filter(pk=pk).update(title=title,desc=desc,thumbnail=thumbnail,content=content,category=category)
            return restful.ok()
        else:
            return restful.paramserror(message=form.get_errors())

@require_GET
def news_category(request):
    categories = NewsCategory.objects.all()
    context = {
        'categories':categories
    }
    return render(request,'cms/news_category.html',context=context)

@require_POST
def add_news_category(request):
    name = request.POST.get('name')
    exists = NewsCategory.objects.filter(name=name).exists()
    if not exists:
        NewsCategory.objects.create(name=name)
        return restful.ok()
    else:
        return restful.paramserror(message="该分类已存在!")

@require_POST
def edit_news_category(request):
    #form表单验证数据
    form = EditNewsCategoryForm(request.POST)
    if form.is_valid():
        pk = form.cleaned_data.get('pk')
        name = form.cleaned_data.get('name')
        try:
            NewsCategory.objects.filter(pk=pk).update(name=name)
            return restful.ok()
        except:
            return restful.paramserror(message="不存在该分类!")
    else:
        return restful.paramserror(message=form.get_errors())

@require_POST
def delete_news_category(request):
    pk = request.POST.get('pk')
    try:
        NewsCategory.objects.filter(pk=pk).delete()
        return restful.ok()
    except:
        return restful.paramserror(message="不存在该分类!")


@require_POST
def upload_file(request):
    file = request.FILES.get('file')
    name = file.name
    with open(os.path.join(settings.MEDIA_ROOT,name),'wb') as fp:
        for chunk in file.chunks():
            fp.write(chunk)
    url = request.build_absolute_uri(settings.MEDIA_URL+name)
    return restful.result(data={'url':url})


@require_GET
def qntoken(request):
    access_key = settings.QINIU_ACCESS_KEY
    secret_key = settings.QINIU_SECRET_KEY
    q = qiniu.Auth(access_key,secret_key)

    bucket = settings.QINIU_BUCKET_NAME
    token = q.upload_token(bucket) #返回给js代码 与七牛云交互
    return restful.result(data={'token':token})

def banner(request):
    return render(request,'cms/banners.html')



#前后端分离的方式，前端调用接口，把后端的数据list列表通过js渲染出来
def banner_list(request):
    banners = Banner.objects.all() #提取所有的轮播图
    serialize = BannerSerializer(banners,many=True)
    return restful.result(data=serialize.data)


def add_banner(request):
    #表单验证
    form = AddBannerForm(request.POST)
    if form.is_valid():
        priority = form.cleaned_data.get('priority')
        link_to = form.cleaned_data.get('link_to')
        image_url = form.cleaned_data.get('image_url')

        banner = Banner.objects.create(priority=priority,link_to=link_to,image_url=image_url)
        return restful.result(data={"banner_id":banner.pk})
    else:
        return restful.paramserror(message=form.get_errors())

#删除轮播图
def delete_banner(request):
    banner_id = request.POST.get('banner_id')
    Banner.objects.filter(pk=banner_id).delete()
    return restful.ok()

def edit_banner(request):
    form = UpdateBannerForm(request.POST)
    if form.is_valid():
        pk = form.cleaned_data.get('pk')
        priority = form.cleaned_data.get('priority')
        link_to = form.cleaned_data.get('link_to')
        image_url = form.cleaned_data.get('image_url')
        Banner.objects.filter(pk=pk).update(image_url=image_url, link_to=link_to, priority=priority)
        return restful.ok()
    else:
        return restful.paramserror(message=form.get_errors())

def delete_news(request):
    news_id = request.POST.get('news_id');
    News.objects.filter(pk=news_id).delete()
    return restful.ok()