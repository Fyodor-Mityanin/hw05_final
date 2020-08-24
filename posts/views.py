from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_page
from .forms import PostForm, CommentForm
from .models import Group, Post, User, Follow


@cache_page(20)
def index(request):
    post_list = Post.objects.all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request,
        'index.html',
        {'page': page, 'paginator': paginator}
    )


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    group_post_list = group.posts.all()
    paginator = Paginator(group_post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request,
        'group.html',
        {
            'page': page,
            'paginator': paginator,
        }
    )


@login_required
def new_post(request):
    form = PostForm(request.POST or None, files=request.FILES or None,)
    if request.method == 'POST' and form.is_valid():
        form.instance.author = request.user
        form.save()
        return redirect('index')
    return render(
        request,
        'new_post.html',
        {'form': form, }
    )


def profile(request, username):
    username = get_object_or_404(User, username=username)
    author_post_list = username.posts.all()
    follow = Follow.objects.filter(user=request.user, author=username)
    print('~~~~~~~~~~~~~~~~~~~~~~~~~~~')
    print(follow)
    print('~~~~~~~~~~~~~~~~~~~~~~~~~~~')
    paginator = Paginator(author_post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request,
        'profile.html',
        {
            'page': page,
            'paginator': paginator,
            'profile': username,
            'follow': follow,
        }
    )


def post_view(request, username, post_id):
    post = get_object_or_404(Post, author__username=username, pk=post_id)
    form = CommentForm(request.POST or None)
    comments = post.comments.all()
    if request.method == 'POST' and form.is_valid():
        form.instance.author = request.user
        form.instance.post = post
        form.save()
        return redirect('post', username=username, post_id=post_id)
    return render(
        request,
        'post.html',
        {
            'profile': post.author,
            'post': post,
            'form': form,
            'comments': comments,
        }
    )


@login_required
def post_edit(request, username, post_id):
    post = get_object_or_404(Post, author__username=username, pk=post_id)
    if post.author != request.user:
        return redirect('post', username=username, post_id=post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('post', username=username, post_id=post_id)
    return render(
        request,
        'new_post.html',
        {
            'form': form,
            'post': post,
        }
    )


@login_required
def add_comment(request, username, post_id):
    post = get_object_or_404(Post, author__username=username, pk=post_id)
    form = CommentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.instance.author = request.user
        form.instance.post = post
        form.save()
    return redirect('post', username=username, post_id=post_id)


def page_not_found(request, exception):
    return render(
        request,
        "misc/404.html",
        {"path": request.path},
        status=404
    )


def server_error(request):
    return render(request, "misc/500.html", status=500)


@login_required
def follow_index(request):
    authors_qs = request.user.follower.all()

    print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
    print(authors_qs)
    print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
    post_list = Post.objects.filter(author__id__in=authors_qs)
    print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
    print(post_list)
    print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')

    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request,
        'follow.html',
        {'page': page, 'paginator': paginator}
    )

    return render(request, "follow.html", {...})


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    follow = Follow.objects.filter(user=request.user, author=author)
    if not follow and request.user != author:
        Follow.objects.create(
            user=request.user,
            author=author,
        )
    return redirect('profile', username=username)


@login_required
def profile_unfollow(request, username):
    follow = Follow.objects.filter(user=request.user, author__username=username)
    if follow:
        follow.delete()
    return redirect('profile', username=username)
