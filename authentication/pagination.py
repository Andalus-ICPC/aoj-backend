from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


def pagination(request, obj_list, max_per_page=25):
    if obj_list == None:
        obj_list = []
    page_number = request.GET.get('page', 1)
    paginator = Paginator(obj_list, max_per_page) # Show 25 submits per page.

    try:
        obj_list = paginator.page(page_number)
    except PageNotAnInteger:
        obj_list = paginator.page(1)
    except EmptyPage:
        obj_list = paginator.page(paginator.num_pages)

    return obj_list, paginator

def page_number_pagination(request, obj_list, page_number, max_per_page=25):
    if obj_list == None:
        obj_list = []
    paginator = Paginator(obj_list, max_per_page) # Show 25 submits per page.

    try:
        obj_list = paginator.page(page_number)
    except PageNotAnInteger:
        obj_list = paginator.page(1)
    except EmptyPage:
        obj_list = paginator.page(paginator.num_pages)

    return obj_list, paginator