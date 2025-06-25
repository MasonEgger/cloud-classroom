# LEGACY: This file is deprecated - use services/digitalocean.py instead
# TODO: Remove after migrating remaining functions to services layer

import crypt

import xkcdpass.xkcd_password as xp

# LEGACY: These constants are unused - modern client handles API calls


def hashpwd(pwd):
    """
    Hash a password using crypt.
    
    NOTE: This function uses a hardcoded salt for backwards compatibility.
    In production, consider using Django's password hashing instead.
    """
    # Using hardcoded salt for backwards compatibility with existing droplets
    # For new implementations, use Django's make_password() function
    hashed_pwd = crypt.crypt(pwd, "$6$saltsalt$")

    return hashed_pwd


def mkpasswd():
    words = xp.locate_wordfile()
    mywords = xp.generate_wordlist(wordfile=words, min_length=5, max_length=8)
    pwd = xp.generate_xkcdpassword(mywords)

    return pwd.lower()


# LEGACY: Replaced by DigitalOceanClient.list_regions()
def list_regions(token):
    # Use services.digitalocean.DigitalOceanClient instead
    pass


# LEGACY: Replaced by DigitalOceanClient.list_sizes()
def list_sizes(token):
    # Use services.digitalocean.DigitalOceanClient instead
    pass


# LEGACY: Replaced by DigitalOceanClient.list_images()
def list_images():
    # Use services.digitalocean.DigitalOceanClient instead
    # These hardcoded images are outdated
    pass


# LEGACY: Replaced by DigitalOceanClient.power_off_droplet()
def power_off(token, droplet_id):
    # Use services.digitalocean.DigitalOceanClient instead
    pass


# LEGACY: Replaced by DigitalOceanClient.power_on_droplet()
def power_on(token, droplet_id):
    # Use services.digitalocean.DigitalOceanClient instead
    pass


# LEGACY: Replaced by DigitalOceanClient.get_droplet()
def power_status(token, droplet_id):
    # Use services.digitalocean.DigitalOceanClient instead
    pass


# LEGACY: Replaced by DigitalOceanClient.delete_droplet()
def destroy(token, droplet_id):
    # Use services.digitalocean.DigitalOceanClient instead
    pass


"""
    droplet = digitalocean.Droplet(token=token, id=droplet_id)
    try:
        droplet.destroy()
    except NotFoundError:
        pass

    droplet_obj = Droplet.objects.get(droplet_id=droplet_id)
    droplet_obj.class_id.droplet_count = (
        droplet_obj.class_id.droplet_count - 1
    )
    droplet_obj.class_id.save()
    droplet_obj.delete() """


# LEGACY: Replaced by DigitalOceanClient.list_droplets()
def list_droplets(token, prefix):
    # Use services.digitalocean.DigitalOceanClient instead
    pass


"""
    manager = digitalocean.Manager(token=token)
    all_droplets = manager.get_all_droplets()
    droplets = []
    for d in all_droplets:
        if d.name.startswith(prefix):
            d.initial_pass = Droplet.objects.get(droplet_id=d.id).initial_pwd
            droplets.append(d)

    return droplets """


# LEGACY: Replaced by ClassroomService.create_droplet_for_student()
def add_droplet(token, class_obj, owner):
    # Use services.classroom.ClassroomService instead
    pass


"""
    size = class_obj.droplet_size

    user = "ubuntu"
    expire = True

    pwd = mkpasswd()
    data = cloud_config.format(user, user, pwd, expire)
    name = (
        class_obj.prefix
        + "-"
        + owner.email.replace("@", "-AT-")
        + "-"
        + pwd.split(" ")[0]
    )

    droplet_data = {
        "token": token,
        "size_slug": class_obj.droplet_size,
        "region": class_obj.droplet_region,
        "name": name,
        "image": class_obj.droplet_image,
        "user_data": data,
    }
    if class_obj.force_teacher_ssh_key is True:
        teachers = class_obj.teacher_set.all()
        ssh_keys = []
        for teacher in teachers:
            try:
                prof = Profile.objects.get(user=teacher.user)
                if prof.ssh_key != "":
                    ssh_keys.append(prof.ssh_key)
            except Profile.DoesNotExist:
                pass
        if len(ssh_keys) > 0:
            droplet_data["ssh_keys"] = ssh_keys

    droplet = digitalocean.Droplet(**droplet_data)
    droplet.create()
    # have to load the droplet to get the IP address
    while droplet.ip_address is None:
        time.sleep(1)
        try:
            droplet.load()
        except digitalocean.DataReadError:
            print("{0} waiting to load".format(droplet.name))
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

    return {
        "droplet_id": droplet.id,
        "droplet_ip": droplet.ip_address,
        "user": user,
        "initial_password": pwd,
    } """


# LEGACY: Replaced by ClassroomService.destroy_class_droplets()
def end_class(token, class_obj):
    # Use services.classroom.ClassroomService instead
    pass


"""     droplets = Droplet.objects.filter(group=class_obj)
    for d in droplets:
        if not d.destroyed_at:
            droplet = digitalocean.Droplet(token=token, id=d.droplet_id)
            try:
                droplet.destroy()
                droplets.update(destroyed_at=datetime.now())
            except NotFoundError:
                pass
    class_obj.destroyed_at = datetime.now()
    class_obj.save() """


# NOTE: This cloud-init template is duplicated in droplet/models.py
# TODO: Consolidate into a single location in services layer
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
