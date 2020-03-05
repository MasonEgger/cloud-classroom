from django.contrib.auth.models import User
from classes.models import Teacher, Class
from droplet.models import Droplet

import digitalocean
from digitalocean.baseapi import NotFoundError
import xkcdpass.xkcd_password as xp
from datetime import datetime
import time
import os
import crypt


def hashpwd(pwd):
    hashed_pwd = crypt.crypt(pwd, "$6$saltsalt$")

    return hashed_pwd


def mkpasswd():
    words = xp.locate_wordfile()
    mywords = xp.generate_wordlist(
        wordfile=words, min_length=5, max_length=8
    )
    pwd = xp.generate_xkcdpassword(mywords)

    return pwd.lower()


def list_regions():
    token = BillableAccount.objects.get(pk=1).token
    manager = digitalocean.Manager(token=token)
    all_regions = manager.get_all_regions()

    regions = []
    for r in all_regions:
        if "metadata" in r.features:
            regions.append((r.slug, r.name))

    return regions


def list_sizes():
    token = BillableAccount.objects.get(pk=1).token
    manager = digitalocean.Manager(token=token)
    all_sizes = manager.get_all_sizes()

    sizes = []
    for s in all_sizes:
        if s.available:
            sizes.append((s.slug, s.slug))

    return sizes


def list_images():
    """
    List of available images.
    
    Some hard coding is needed as images using cloud-init aren't
    specified in the API.
    """
    images = [
        ("ubuntu-14-04-x64", "Ubuntu 14.04 x64"),
        ("ubuntu-14-10-x64", "Ubuntu 14.10 x64"),
        ("ubuntu-15-04-x64", "Ubuntu 15.04 x64"),
        ("docker", "Docker on Ubuntu 14.04"),
        ("lamp", "LAMP on Ubuntu 14.04"),
        ("lemp", "LEMP on Ubuntu 14.04"),
        ("node", "Node.js on Ubuntu 14.04"),
        ("mongodb", "MongoDB on Ubuntu 14.04"),
    ]

    # token = Teacher.objects.get(pk=1).token
    # manager = digitalocean.Manager(token=token)
    # all_images = manager.get_app_images()
    # for i in all_images:
    #     images.append((i.slug, i.name))

    return images


def power_off(token, droplet_id):
    droplet = digitalocean.Droplet(token=token, id=droplet_id)
    droplet.shutdown()


def power_on(token, droplet_id):
    droplet = digitalocean.Droplet(token=token, id=droplet_id)
    droplet.power_on()


def destroy(token, droplet_id):
    droplet = digitalocean.Droplet(token=token, id=droplet_id)
    resp = droplet.destroy()

    if resp:
        droplet_obj = Droplet.objects.get(droplet_id=droplet_id)
        droplet_obj.class_id.droplet_count = (
            droplet_obj.class_id.droplet_count - 1
        )
        droplet_obj.class_id.save()
        droplet_obj.delete()


def list_droplets(token, prefix):
    manager = digitalocean.Manager(token=token)
    all_droplets = manager.get_all_droplets()
    droplets = []
    for d in all_droplets:
        if d.name.startswith(prefix):
            d.initial_pass = Droplet.objects.get(droplet_id=d.id).initial_pwd
            droplets.append(d)

    return droplets


def add_droplet(token, class_obj, owner):
    size = class_obj.droplet_size
    user = "ubuntu"
    expire = True
    count = class_obj.droplet_count + 1

    pwd = mkpasswd()
    hashed_pwd = hashpwd(pwd)
    data = cloud_config.format(user, user, pwd, expire)
    name = (
        class_obj.prefix
        + "-"
        + owner.user.username
        + "-"
        + str(count).zfill(3)
    )

    droplet = digitalocean.Droplet(
        token=token,
        size_slug=class_obj.droplet_size,
        region=class_obj.droplet_region,
        name=name,
        image=class_obj.droplet_image,
        user_data=data,
    )
    droplet.create()
    # have to load the droplet to get the IP address
    while droplet.ip_address is None:
        time.sleep(1)
        droplet.load()
    print(droplet.ip_address)
    droplet_obj = Droplet(
        name=name,
        class_id=class_obj,
        droplet_id=droplet.id,
        initial_password=pwd,
        region=class_obj.droplet_region,
        image=droplet.image,
        ip_addr=droplet.ip_address,
        owner=owner,
    )
    droplet_obj.save()
    class_obj.droplet_count = count
    class_obj.save()


def launch_droplets(request, class_obj):
    user = Teacher.objects.get(user=request.user.id)
    token = user.token
    size = class_obj.droplet_size
    pkgs = apt_packages(class_obj.packages)
    user = "ubuntu"
    expire = True

    count = 0
    while count < class_obj.droplet_count:
        pwd = mkpasswd()
        hashed_pwd = hashpwd(pwd)
        data = cloud_config.format(pkgs, user, user, pwd, expire)
        name = class_obj.prefix + "-" + str(count + 1).zfill(3)
        print(class_obj.droplet_size)
        droplet = digitalocean.Droplet(
            token=token,
            size_slug=class_obj.droplet_size,
            region=class_obj.droplet_region,
            name=name,
            image=class_obj.droplet_image,
            user_data=data,
        )
        droplet.create()

        droplet_obj = Droplet(
            group=class_obj, droplet_id=droplet.id, initial_pwd=pwd
        )
        droplet_obj.save()
        count = count + 1


def end_class(token, class_obj):
    droplets = Droplet.objects.filter(group=class_obj)
    for d in droplets:
        if not d.destroyed_at:
            droplet = digitalocean.Droplet(token=token, id=d.droplet_id)
            try:
                droplet.destroy()
                droplets.update(destroyed_at=datetime.now())
            except NotFoundError:
                pass
    class_obj.destroyed_at = datetime.now()
    class_obj.save()


cloud_config = """
#cloud-config
users:
  - name: {}
    groups: sudo
    shell: /bin/bash
    sudo: ['ALL=(ALL:ALL) ALL']
    lock-passwd: false
chpasswd:
  list: |
    {}:{}
  expire: {}
runcmd:
 - passwd -l root
"""
