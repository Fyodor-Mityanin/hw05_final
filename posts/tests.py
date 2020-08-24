from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from .models import Group, Post, User


class Test_all(TestCase):
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
        self.post_text = 'I say we take off and nuke this entire site from orbit...its the only way to be sure.'

    def tearDown(self):
        cache.clear()

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

    def test_post_contains_img(self):
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
        post_link = reverse(
            'post',
            kwargs={
                'username': self.user.username,
                'post_id': post.id,
            }
        )
        response = self.unauth_client.get(post_link)
        self.assertContains(response, '<img')

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
        Post.objects.create(
            author=self.user,
            text='post with image',
            group=self.group,
            image=img,
        )
        urls = [
            reverse('index'),
            self.profile_link(),
            self.group_link(),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.unauth_client.get(url)
                self.assertContains(response, '<img')

    def test_not_img_cannot_upload(self):
        with open('media/tests/just_text.txt', 'rb') as img:
            post = self.auth_client.post(
                reverse('new_post'),
                {
                    'text': 'post with image',
                    'group': self.group.id,
                    'image': img,
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
        post1 = Post.objects.create(
            text=self.post_text,
            author=self.user,
            group=self.group,
        )
        response = self.unauth_client.get(reverse('index'))
        self.assertContains(response, post1.text)
        post2 = Post.objects.create(
            text='new_text',
            author=self.user,
        )
        response = self.unauth_client.get(reverse('index'))
        self.assertNotContains(response, post2.text)
        cache.clear()
        response = self.unauth_client.get(reverse('index'))
        self.assertContains(response, post2.text)

    def test_auth_user_can_follow_and_unfollow(self):
        user2 = User.objects.create_user(username='bishop')
        follow_link = reverse('profile_follow', args=[user2.username])
        unfollow_link = reverse('profile_unfollow', args=[user2.username])
        self.assertEqual(self.user.follower.count(), 0)
        self.auth_client.get(follow_link)
        self.assertEqual(self.user.follower.count(), 1)
        self.auth_client.get(unfollow_link)
        self.assertEqual(self.user.follower.count(), 0)

    def test_new_post_apears_in_follow(self):
        user2 = User.objects.create_user(username='bishop')
        Post.objects.create(
            text=self.post_text,
            author=user2,
            group=self.group,
        )
        follow_link = reverse('profile_follow', args=[user2.username])
        unfollow_link = reverse('profile_unfollow', args=[user2.username])
        response = self.auth_client.get(reverse('follow_index'))
        self.assertEqual(response.context['paginator'].count, 0)
        self.auth_client.get(follow_link)
        response = self.auth_client.get(reverse('follow_index'))
        self.assertEqual(response.context['paginator'].count, 1)
        self.auth_client.get(unfollow_link)
        response = self.auth_client.get(reverse('follow_index'))
        self.assertEqual(response.context['paginator'].count, 0)

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
        self.assertEqual(post.comments.count(), 0)
        self.assertEqual(self.user.comments.count(), 0)
        self.auth_client.post(
            add_comment_link,
            {
                'text': 'каммент',
            }
        )
        self.assertEqual(post.comments.count(), 1)
        self.assertEqual(self.user.comments.count(), 1)
