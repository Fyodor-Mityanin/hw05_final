import os
import shutil

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from yatube.settings import BASE_DIR

from .models import Comment, Follow, Group, Post, User

TEST_MEDIA_ROOT = os.path.join(BASE_DIR, 'test_data')


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class TestAll(TestCase):
    def setUp(self):
        self.auth_client = Client()
        self.unauth_client = Client()
        self.user = User.objects.create_user(
            username='ripley',
        )
        self.auth_client.force_login(self.user)
        self.group = Group.objects.create(
            title='Чужие',
            slug='aliens',
            description='Группа посвящённая проблемам с ксеноморфами',
        )
        self.post_text = ('I say we take off and nuke this entire '
                          'site from orbit...its the only way to be sure.')
        cache.clear()

    def tearDown(self):
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def profile_link(self):
        return reverse('profile', kwargs={'username': self.user.username, })

    def group_link(self):
        return reverse('group', kwargs={'slug': self.group.slug, })

    def test_profile_page_exist(self):
        response = self.unauth_client.get(self.profile_link())
        self.assertEqual(response.status_code, 200)

    def test_auth_user_can_create_post(self):
        self.auth_client.post(
            reverse('new_post'),
            {
                'text': self.post_text,
                'group': self.group.id,
            }
        )
        self.assertEqual(Post.objects.count(), 1)
        user_post = self.user.posts.first()
        self.assertEqual(user_post.text, self.post_text)
        self.assertEqual(user_post.author, self.user)
        self.assertEqual(user_post.group, self.group)

    def test_anonymous_cant_create_post(self):
        response = self.unauth_client.post(
            reverse('new_post'),
            {
                'text': self.post_text,
                'group': self.group.id,
            }
        )
        self.assertRedirects(
            response,
            reverse('login') + '?next=' + reverse('new_post'),
            target_status_code=200,
            msg_prefix='Чёт не редиректит',
            fetch_redirect_response=True
        )
        self.assertEqual(Post.objects.count(), 0)

    def check_post_context(self, resp, text, user, group):
        if 'post' in resp.context:
            obj = resp.context['post']
        else:
            obj = resp.context['page'][0]
            self.assertEqual(resp.context['paginator'].count, 1)
        self.assertEqual(obj.text, text)
        self.assertEqual(obj.author, user)
        self.assertEqual(obj.group, group)

    def test_new_post_appears_everywhere(self):
        post = Post.objects.create(
            text=self.post_text,
            author=self.user,
            group=self.group,
        )
        post_link = reverse(
            'post',
            kwargs={
                'username': self.user.username,
                'post_id': post.id
            }
        )
        urls = [
            reverse('index'),
            self.profile_link(),
            post_link,
            self.group_link(),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.unauth_client.get(url)
                self.check_post_context(
                    resp=response,
                    text=self.post_text,
                    user=self.user,
                    group=self.group
                )

    def test_edited_post_changes_everywhere(self):
        post = Post.objects.create(
            text=self.post_text,
            author=self.user,
            group=self.group,
        )
        post_link = reverse(
            'post',
            kwargs={
                'username': self.user.username,
                'post_id': post.id
            }
        )
        post_edit_link = reverse(
            'post_edit',
            kwargs={
                'username': self.user.username,
                'post_id': post.id,
            }
        )
        self.new_group = Group.objects.create(
            title='Weyland-Yutani Corp.',
            slug='weylandyutani',
            description='Официальный паблик «Weyland-Yutani Corporation»',
        )
        self.post_edited_text = ('These people are here to protect you. '
                                 'They are soldiers.')
        self.auth_client.post(
            post_edit_link,
            {
                'text': self.post_edited_text,
                'group': self.new_group.id,
            }
        )
        new_group_link = reverse(
            'group',
            kwargs={'slug': self.new_group.slug, }
        )
        urls = [
            reverse('index'),
            self.profile_link(),
            post_link,
            new_group_link,
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.unauth_client.get(url)
                self.check_post_context(
                    resp=response,
                    text=self.post_edited_text,
                    user=self.user,
                    group=self.new_group
                )
        response_group = self.unauth_client.get(self.group_link())
        self.assertEqual(response_group.context['paginator'].count, 0)

    def test_if_page_not_found_404(self):
        response = self.unauth_client.get('/sagertynryunryunfgnv/')
        self.assertEqual(response.status_code, 404)

    def test_img_appears_everywhere(self):
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        img = SimpleUploadedFile(
            name='img.gif',
            content=small_gif,
            content_type='image/jpeg',
        )
        post = Post.objects.create(
            author=self.user,
            text='post with image',
            group=self.group,
            image=img,
        )
        urls = [
            reverse('index'),
            self.profile_link(),
            self.group_link(),
            reverse('post', args=[self.user.username, post.id]),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.unauth_client.get(url)
                self.assertContains(response, '<img')

    def test_not_img_cannot_upload(self):
        text_file = (b'text')
        not_img = SimpleUploadedFile(
            name='not_img.jpg',
            content=text_file,
            content_type='image/jpeg',
        )
        post = self.auth_client.post(
            reverse('new_post'),
            {
                'text': 'post with image',
                'group': self.group.id,
                'image': not_img,
            },
        )
        self.assertFormError(
            post,
            'form',
            'image',
            ('Загрузите правильное изображение. '
             'Файл, который вы загрузили,'
             ' поврежден или не является изображением.')
        )

    def test_cache(self):
        post = Post.objects.create(
            text=self.post_text,
            author=self.user,
            group=self.group,
        )
        response_before_post_delete = self.unauth_client.get(reverse('index'))
        self.check_post_context(
            resp=response_before_post_delete,
            text=self.post_text,
            user=self.user,
            group=self.group
        )
        post.delete()
        response_after_post_delete = self.unauth_client.get(reverse('index'))
        self.assertEqual(
            response_before_post_delete.content,
            response_after_post_delete.content
        )
        cache.clear()
        response_after_cache_clear = self.unauth_client.get(reverse('index'))
        self.assertNotEqual(
            response_before_post_delete.content,
            response_after_cache_clear.content
        )

    def test_auth_user_can_follow(self):
        user2 = User.objects.create_user(username='bishop')
        follow_link = reverse('profile_follow', args=[user2.username])
        self.auth_client.get(follow_link)
        self.assertEqual(Follow.objects.count(), 1)
        follow_obj = Follow.objects.first()
        self.assertEqual(follow_obj.author, user2)
        self.assertEqual(follow_obj.user, self.user)

    def test_auth_user_can_unfollow(self):
        user2 = User.objects.create_user(username='bishop')
        Follow.objects.create(
            user=self.user,
            author=user2,
        )
        unfollow_link = reverse('profile_unfollow', args=[user2.username])
        self.auth_client.get(unfollow_link)
        self.assertEqual(self.user.follower.count(), 0)

    def test_new_post_apears_in_follow(self):
        user2 = User.objects.create_user(username='bishop')
        Post.objects.create(
            text=self.post_text,
            author=user2,
            group=self.group,
        )
        Follow.objects.create(
            user=self.user,
            author=user2,
        )
        response = self.auth_client.get(reverse('follow_index'))
        self.check_post_context(
            resp=response,
            text=self.post_text,
            user=user2,
            group=self.group
        )

    def test_auth_user_can_comment(self):
        user2 = User.objects.create_user(username='bishop')
        post = Post.objects.create(
            text=self.post_text,
            author=user2,
            group=self.group,
        )
        add_comment_link = reverse(
            'add_comment',
            kwargs={
                'username': user2.username,
                'post_id': post.id,
            }
        )
        comment_text = 'каммент'
        self.auth_client.post(add_comment_link, {'text': comment_text})
        self.assertEqual(Comment.objects.count(), 1)
        comment = Comment.objects.first()
        self.assertEqual(comment.post, post)
        self.assertEqual(comment.author, self.user)
        self.assertEqual(comment.text, comment_text)

    def test_unauth_user_can_comment(self):
        post = Post.objects.create(
            text=self.post_text,
            author=self.user,
            group=self.group,
        )
        add_comment_link = reverse(
            'add_comment',
            kwargs={
                'username': self.user.username,
                'post_id': post.id,
            }
        )
        comment_text = 'каммент'
        self.unauth_client.post(add_comment_link, {'text': comment_text})
        self.assertFalse(Comment.objects.exists())
