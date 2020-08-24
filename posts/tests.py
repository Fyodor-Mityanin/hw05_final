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

    def profile_link(self):
        return reverse('profile', kwargs={'username': self.user.username, })

    def group_link(self):
        return reverse('group', kwargs={'slug': self.group.slug, })

    def test_profile_page_exist(self):
        response = self.unauth_client.get(self.profile_link())
        self.assertEqual(response.status_code, 200)

    def test_login_user_can_create_post(self):
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
        response_index = self.unauth_client.get(reverse('index'))
        response_profile = self.unauth_client.get(self.profile_link())
        response_post = self.unauth_client.get(post_link)
        response_group = self.unauth_client.get(self.group_link())

        response_list = [response_index, response_profile,
                         response_post, response_group, ]

        for response in response_list:
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
        self.post_edited_text = 'These people are here to protect you. They are soldiers.'
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
        response_index = self.unauth_client.get(reverse('index'))
        response_profile = self.unauth_client.get(self.profile_link())
        response_post = self.unauth_client.get(post_link)
        response_group = self.unauth_client.get(self.group_link())
        response_new_group = self.unauth_client.get(new_group_link)

        response_list = [response_index, response_profile,
                         response_post, response_new_group, ]

        for response in response_list:
            self.check_post_context(
                resp=response,
                text=self.post_edited_text,
                user=self.user,
                group=self.new_group
            )

        self.assertEqual(response_group.context['paginator'].count, 0)

    def test_if_page_not_found_404(self):
        response = self.unauth_client.get('/sagertynryunryunfgnv/')
        self.assertEqual(response.status_code, 404)

    def test_post_contains_img(self):
        with open('media/tests/test_img.JPG', 'rb') as img:
            self.auth_client.post(
                reverse('new_post'),
                {
                    'text': 'post with image',
                    'group': self.group.id,
                    'image': img,
                },
            )
        post_link = reverse(
            'post',
            kwargs={
                'username': self.user.username,
                'post_id': 1,
            }
        )
        response = self.unauth_client.get(post_link)
        self.assertIn('img', response.content.decode())

    def test_img_appears_everywhere(self):
        with open('media/tests/test_img.JPG', 'rb') as img:
            self.auth_client.post(
                reverse('new_post'),
                {
                    'text': 'post with image',
                    'group': self.group.id,
                    'image': img,
                },
            )
        response_index = self.unauth_client.get(reverse('index'))
        response_profile = self.unauth_client.get(self.profile_link())
        response_group = self.unauth_client.get(self.group_link())
        response_list = [response_index, response_profile, response_group]
        for response in response_list:
            self.assertIn('img', response.content.decode())

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
             'Файл, который вы загрузили, поврежден или не является изображением.')
        )
