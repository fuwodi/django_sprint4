from datetime import date

from django import forms
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from blog.models import Category, Comment, Post

User = get_user_model()


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'text', 'pub_date', 'location', 'category', 'image']
        widgets = {
            'pub_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3}),
        }


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email']


def index(request):
    today_date = date.today()
    published_posts_qs = (
        Post.objects.select_related("category")
        .filter(
            is_published=True,
            pub_date__lte=today_date,
            category__is_published=True,
        )
        .select_related("category", "location", "author")
        .order_by("-pub_date")
    )

    paginator = Paginator(published_posts_qs, 10)
    page_num = request.GET.get('page')
    requested_page = paginator.get_page(page_num)

    context = {"page_obj": requested_page}
    return render(request, "blog/index.html", context)


def category_posts(request, category_slug):
    today_date = date.today()
    chosen_category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True,
    )
    category_posts_qs = Post.objects.filter(
        category=chosen_category,
        is_published=True,
        pub_date__lte=today_date,
    ).select_related("category", "location", "author").order_by("-pub_date")

    paginator = Paginator(category_posts_qs, 10)
    page_num = request.GET.get('page')
    requested_page = paginator.get_page(page_num)

    context = {
        "page_obj": requested_page,
        "category": chosen_category,
    }
    return render(request, "blog/category.html", context)


def post_detail(request, id):
    today_date = date.today()

    target_post = get_object_or_404(Post, id=id)

    if request.user != target_post.author:
        target_post = get_object_or_404(
            Post,
            id=id,
            is_published=True,
            pub_date__lte=today_date,
            category__is_published=True,
        )

    post_comments_qs = target_post.comments.all()
    comment_form = CommentForm()
    template_context = {
        "post": target_post,
        "comments": post_comments_qs,
        "form": comment_form,
    }
    return render(request, "blog/detail.html", template_context)


@login_required
def create_post(request):
    if request.method == 'POST':
        post_form = PostForm(request.POST, request.FILES)
        if post_form.is_valid():
            new_post = post_form.save(commit=False)
            new_post.author = request.user
            new_post.save()
            return redirect('blog:profile', username=request.user.username)
    else:
        post_form = PostForm()

    return render(request, "blog/create.html", {'form': post_form})


@login_required
def edit_post(request, post_id):
    edited_post = get_object_or_404(Post, id=post_id)

    if edited_post.author != request.user:
        return redirect('blog:post_detail', id=post_id)

    if request.method == 'POST':
        post_form = PostForm(request.POST, request.FILES, instance=edited_post)
        if post_form.is_valid():
            post_form.save()
            return redirect('blog:post_detail', id=post_id)
    else:
        post_form = PostForm(instance=edited_post)

    return render(
        request,
        "blog/create.html",
        {'form': post_form, 'post': edited_post},
    )


@login_required
def delete_post(request, post_id):
    removable_post = get_object_or_404(Post, id=post_id)

    if removable_post.author != request.user:
        return redirect('blog:post_detail', id=post_id)

    if request.method == 'POST':
        removable_post.delete()
        return redirect('blog:index')

    return render(request, "blog/delete.html", {"post": removable_post})


def profile(request, username):
    today_date = date.today()
    profile_user = get_object_or_404(User, username=username)

    if request.user == profile_user:
        profile_posts_qs = Post.objects.filter(
            author=profile_user,
        ).order_by("-pub_date")
    else:
        profile_posts_qs = Post.objects.filter(
            author=profile_user,
            is_published=True,             
            pub_date__lte=today_date,      
            category__is_published=True,   
        ).select_related("category", "location", "author").order_by("-pub_date")

        #profile_posts_qs = Post.objects.filter(
            #author=profile_user,
            #category__is_published=True,
        #).order_by("-pub_date")

    paginator = Paginator(profile_posts_qs, 10)
    page_num = request.GET.get('page')
    requested_page = paginator.get_page(page_num)

    context = {
        "profile": profile_user,
        "page_obj": requested_page,
    }
    return render(request, "blog/profile.html", context)


@login_required
def edit_profile(request, username):
    profile_owner = get_object_or_404(User, username=username)

    if request.user != profile_owner:
        return redirect('blog:profile', username=username)

    if request.method == 'POST':
        profile_form = ProfileEditForm(request.POST, instance=profile_owner)
        if profile_form.is_valid():
            profile_form.save()
            update_session_auth_hash(request, profile_owner)
            return redirect('blog:profile', username=username)
    else:
        profile_form = ProfileEditForm(instance=profile_owner)

    return render(
        request,
        'blog/edit_profile.html',
        {'form': profile_form, 'profile': profile_owner},
    )


@login_required
def add_comment(request, post_id):
    target_post = get_object_or_404(Post, id=post_id)
    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.post = target_post
            new_comment.author = request.user
            new_comment.save()
    return redirect('blog:post_detail', id=post_id)


@login_required
def edit_comment(request, post_id, comment_id):
    edited_comment = get_object_or_404(Comment, id=comment_id, post_id=post_id)

    if edited_comment.author != request.user:
        raise Http404("Комментарий не найден")

    if request.method == 'POST':
        comment_form = CommentForm(request.POST, instance=edited_comment)
        if comment_form.is_valid():
            comment_form.save()
            return redirect('blog:post_detail', id=post_id)
    else:
        comment_form = CommentForm(instance=edited_comment)

    return render(
        request,
        'blog/create.html',
        {'form': comment_form, 'post': edited_comment.post},
    )


@login_required
def delete_comment(request, post_id, comment_id):
    removable_comment = get_object_or_404(Comment, id=comment_id, post_id=post_id)

    if removable_comment.author != request.user:
        raise Http404("Комментарий не найден")

    if request.method == 'POST':
        removable_comment.delete()
        return redirect('blog:post_detail', id=post_id)

    template_context = {
        'comment': removable_comment,
        'post_id': post_id,
        'post': removable_comment.post,
    }

    return render(request, 'blog/delete.html', template_context)
