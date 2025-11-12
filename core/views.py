from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from .models import Post, Profile, Comment
from .forms import RegisterForm, PostForm, CommentForm, ProfileUpdateForm, UserUpdateForm


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Вітаємо! Ваш акаунт створено.')
            return redirect('feed')
    else:
        form = RegisterForm()
    return render(request, 'core/register.html', {'form': form})


@login_required
def feed(request):
    # Пости від користувачів, на яких ми підписані + наші власні
    following_users = request.user.profile.following.values_list('user', flat=True)
    posts = Post.objects.filter(
        Q(author__in=following_users) | Q(author=request.user)
    ).select_related('author', 'author__profile').prefetch_related('likes', 'comments')

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, 'Пост опубліковано!')
            return redirect('feed')
    else:
        form = PostForm()

    return render(request, 'core/feed.html', {'posts': posts, 'form': form})


@login_required
def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    comments = post.comments.select_related('author', 'author__profile')

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            return redirect('post_detail', pk=pk)
    else:
        form = CommentForm()

    return render(request, 'core/post_detail.html', {
        'post': post,
        'comments': comments,
        'form': form
    })


@login_required
def like_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.user in post.likes.all():
        post.likes.remove(request.user)
    else:
        post.likes.add(request.user)
    return redirect(request.META.get('HTTP_REFERER', 'feed'))


@login_required
def delete_post(request, pk):
    post = get_object_or_404(Post, pk=pk, author=request.user)
    post.delete()
    messages.success(request, 'Пост видалено.')
    return redirect('feed')


@login_required
def profile(request, username):
    user = get_object_or_404(User, username=username)
    posts = user.posts.all()
    is_following = request.user.profile.following.filter(user=user).exists()

    return render(request, 'core/profile.html', {
        'profile_user': user,
        'posts': posts,
        'is_following': is_following
    })


@login_required
def edit_profile(request):
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Профіль оновлено!')
            return redirect('profile', username=request.user.username)
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)

    return render(request, 'core/edit_profile.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })


@login_required
def follow_user(request, username):
    user_to_follow = get_object_or_404(User, username=username)
    if user_to_follow != request.user:
        if request.user.profile.following.filter(user=user_to_follow).exists():
            request.user.profile.following.remove(user_to_follow.profile)
        else:
            request.user.profile.following.add(user_to_follow.profile)
    return redirect('profile', username=username)


@login_required
def search(request):
    query = request.GET.get('q', '')
    users = User.objects.filter(
        Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query)
    ).select_related('profile')[:20] if query else []

    return render(request, 'core/search.html', {'users': users, 'query': query})