from django.shortcuts import render
from django.conf import settings

# local imports
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import authentication, permissions
import json
import re
import digitalocean

# model imports

manager = digitalocean.Manager(token=settings.DO_TOKEN)
re_slug = re.compile("^(centos|debian|fedora|ubuntu).+x64$")

# Create your views here.

class list_resources(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        res = {'regions': [], 'images': []}
        res['regions'] = _get_regions()
        res['images'] = _get_images()
        return Response(res)


def _get_regions():
    res = [] # return a list of region objects
    try:
        req = manager.get_all_regions()
        for r in req:
            res.append({"slug":r.slug, "name":r.name})
    except:
        pass
    res = sorted(res, key=lambda k: k['slug'])
    return res


def _get_images():
    res = []
    try:
        req = manager.get_all_images()
        for i in req:
            try:
                if re_slug.match(i.slug):
                    res.append({"slug":i.slug, "name":i.name, "description":i.description, "distribution":i.distribution})
            except:
                pass
    except:
        pass
    res = sorted(res, key=lambda k: k['slug'])
    return res


def _get_droplets():
    res = []
    try:
        req = manager.get_all_droplets()
        if len(req) > 0:
            for d in req:
                res.append({
                    "id":d.id,
                    "name":d.name,
                    "ip_address":d.ip_address,
                    "disk":d.disk,
                    "status":d.status,
                    "tags":d.tags,
                    })
    except:
        res = []
    res = sorted(res, key=lambda k: k['id'])
    return res


def _get_droplet(droplet_id):
    res = {}
    try:
        r = manager.get_droplet(droplet_id)
        if r is not None:
            res['droplet'] = r
        else:
            res['droplet'] = None
    except:
        res = None
    return res
