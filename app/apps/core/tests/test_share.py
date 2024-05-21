import random
import time

from django.test import TestCase
from django.urls import reverse

from core.models import Document, Project
from core.tests.factory import CoreFactory
from users.models import Group, User


class DocumentShareTestCase(TestCase):
    def setUp(self):
        factory = CoreFactory()
        self.owner = User.objects.create(username='owner', email='o@test.com', password='test')
        self.target_user = User.objects.create(username='t1', email='t1@test.com', password='test')
        self.group = Group.objects.create(name='test group')
        self.target_group = User.objects.create(username='t2', email='t2@test.com', password='test')
        self.target_group.groups.add(self.group)
        self.owner.groups.add(self.group)
        self.doc = factory.make_document(owner=self.owner)

    def test_share_with_group(self):
        uri = reverse('document-update', kwargs={'pk': self.doc.pk})
        self.client.force_login(self.target_group)
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 403)

        self.client.force_login(self.owner)
        resp = self.client.post(reverse('document-share', kwargs={'pk': self.doc.pk}), {
            'shared_with_groups': self.group.pk
        })
        self.assertEqual(resp.status_code, 302)

        self.client.force_login(self.target_group)
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)

    def test_share_with_known_user(self):
        uri = reverse('document-update', kwargs={'pk': self.doc.pk})
        self.client.force_login(self.target_user)
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 403)

        self.target_user.groups.add(self.group)
        self.owner.groups.add(self.group)
        self.client.force_login(self.owner)
        resp = self.client.post(reverse('document-share', kwargs={'pk': self.doc.pk}), {
            'shared_with_users': [self.target_user.pk, ]
        })
        self.assertEqual(resp.status_code, 302)

        self.client.force_login(self.target_user)
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)

    def test_share_with_unknown_user(self):
        uri = reverse('document-update', kwargs={'pk': self.doc.pk})
        self.client.force_login(self.target_user)
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 403)

        self.client.force_login(self.owner)
        resp = self.client.post(reverse('document-share', kwargs={'pk': self.doc.pk}), {
            'username': self.target_user.username
        })
        self.assertEqual(resp.status_code, 302)

        self.client.force_login(self.target_user)
        resp = self.client.get(uri)
        self.assertEqual(resp.status_code, 200)

    def test_only_owner_can_share(self):
        self.client.force_login(self.target_user)
        self.assertEqual(self.doc.shared_with_groups.count(), 0)
        resp = self.client.post(reverse('document-share', kwargs={'pk': self.doc.pk}), {
            'share_with_groups': self.group
        })
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(self.doc.shared_with_groups.count(), 0)


class PerformanceShareTestCase(TestCase):
    def setUp(self):
        factory = CoreFactory()

        # make a bunch of groups
        groups = []
        for i in range(100):
            groups.append(factory.make_group())

        # make a bunch of users and assign them to some groups
        users = []
        for i in range(1000):
            u = factory.make_user()
            users.append(u)
            for i in range(i % 3 + 1):
                u.groups.add(random.choice(groups))

        # make a bunch of projects & documents in each
        projects = []
        for i in range(25):
            proj = factory.make_project(owner=random.choice(users), name='proj-%i' % i)
            projects.append(proj)
            for j in range(30):
                factory.make_document(project=proj, name='doc-%i-%i' % (i, j))

        # main user
        user = factory.make_user()
        for group in groups:
            user.groups.add(group)

        # owner of first 5 projects = 150docs
        for proj in projects[:5]:
            proj.owner = user
            proj.save()

        # have been shared 5 projects = 150docs
        for proj in projects[5:10]:
            proj.shared_with_users.add(user)

        # have been shared 5 other projects through one of the groups = 150docs
        for proj in projects[10:15]:
            proj.shared_with_groups.add(random.choice(groups))

        # have been shared some docs of 5 projects = 25docs
        for proj in projects[15:20]:
            for doc in proj.documents.order_by('?')[:5]:
                doc.shared_with_users.add(user)

        # have been shared some docs of 5 projects through one of the groups = 25docs
        for proj in projects[20:25]:
            for doc in proj.documents.order_by('?')[:5]:
                doc.shared_with_groups.add(random.choice(groups))

        self.user = user
        self.startAt = time.time()

    def tearDown(self):
        t = time.time() - self.startAt
        print('%s: %.3f sec' % (self.id(), t))

    def test_project_share_perf(self):
        list(Project.objects.for_user_read(self.user))
        self.assertEqual(Project.objects.for_user_read(self.user).count(), 25)

    def test_doc_share_perf(self):
        print(Document.objects.for_user(self.user).query)
        print('------------------------------')
        print(Document.objects.for_user(self.user).explain(verbose=True, analyze=True))
        print('------------------------------')
        list(Document.objects.for_user(self.user))
        self.assertEqual(Document.objects.for_user(self.user).count(), 150 + 150 + 150 + 25 + 25)
