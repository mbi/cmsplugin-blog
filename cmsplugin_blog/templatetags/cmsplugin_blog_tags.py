import copy, datetime
from django.conf import settings
from django import template
from django.contrib.auth import models as auth_models
from django.db.models import Count
from tagging.models import Tag
from django.core.cache import cache

from cms.utils import get_language_from_request
from cmsplugin_blog.models import Entry, EntryTitle
from cms.models import Placeholder

from simple_translation.translation_pool import translation_pool
from simple_translation.utils import get_translation_filter_language

register = template.Library()


@register.inclusion_tag('cmsplugin_blog/blognav.html', takes_context=True)
def blog_nav(context, entry):
    request = context["request"]
    language =  get_language_from_request(request)
    kw = get_translation_filter_language(Entry, language)
    try:
        previous_entry = entry.get_previous_by_pub_date(**kw)
    except Entry.DoesNotExist:
        previous_entry = None
    try:
        next_entry = entry.get_next_by_pub_date(**kw)
    except Entry.DoesNotExist:
        next_entry = None

    return dict(
        previous_entry=previous_entry,
        next_entry=next_entry,
        request=request
    )


@register.inclusion_tag('cmsplugin_blog/month_links_snippet.html', takes_context=True)
def render_month_links(context):
    request = context["request"]
    language = get_language_from_request(request)
    kw = get_translation_filter_language(Entry, language)
    y_dts = Entry.published.filter(**kw).dates('pub_date', 'year')
    years = cache.get('blog_pub_dates_%s' % language)
    #import ipdb; ipdb.set_trace()
    if years is None:
        years = list()
        for y_dt in y_dts:
            months = list()
            year = y_dt.year
            m_dts = Entry.published.filter(**kw).filter(pub_date__year=year).dates('pub_date', 'month')
            for m_dt in m_dts:
                num_posts = Entry.published.filter(**kw).filter(pub_date__year=year, pub_date__month=m_dt.month).count()
                months.append((m_dt, num_posts))
            years.append((y_dt, months))
        cache.set('blog_pub_dates_%s' % language, years, 60*60)
    return {
        'dates': Entry.published.filter(**kw).dates('pub_date', 'month'),
        'years': years
    }

@register.inclusion_tag('cmsplugin_blog/tag_links_snippet.html', takes_context=True)
def render_tag_links(context):
    request = context["request"]
    language = get_language_from_request(request)
    kw = get_translation_filter_language(Entry, language)
    filters = dict(is_published=True, pub_date__lte=datetime.datetime.now(), **kw)
    return {
        'tags': Tag.objects.usage_for_model(Entry, filters=filters)
    }

@register.inclusion_tag('cmsplugin_blog/author_links_snippet.html', takes_context=True)
def render_author_links(context, order_by='username'):
    request = context["request"]
    language = get_language_from_request(request)
    info = translation_pool.get_info(Entry)
    model = info.translated_model
    kw = get_translation_filter_language(Entry, language)
    return {
        'authors': auth_models.User.objects.filter(
            pk__in=model.objects.filter(
                entry__in=Entry.published.filter(**kw)
            ).values('author')
        ).order_by(order_by)  # .values_list('username', flat=True)
    }

@register.filter
def choose_placeholder(placeholders, placeholder):
    try:
        return placeholders.get(slot=placeholder)
    except Placeholder.DoesNotExist:
        return None


@register.inclusion_tag('admin/cmsplugin_blog/admin_helpers.html', takes_context=True)
def admin_helpers(context):
    context = copy.copy(context)
    context.update({
        'use_missing': 'missing' in settings.INSTALLED_APPS,
    })
    return context


@register.inclusion_tag('cmsplugin_blog/last_posts_links_snippet.html', takes_context=True)
def render_last_posts(context):
    request = context["request"]
    language = get_language_from_request(request)
    kw = get_translation_filter_language(Entry, language)
    return {
        'posts': Entry.published.filter(**kw),
        'request': request
    }
