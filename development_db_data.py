from users.models import User
from students.models import Student
from teachers.models import Teacher
from classes.models import Class
from droplet.utils.do_utils import mkpasswd

user1 = User(
    email="mmcgonagall@hogwarts.edu",
    first_name="Minerva",
    last_name="McGonagall",
    is_active=True,
    password=mkpasswd(),
)
user1.save()

user2 = User(
    email="ssnape@hogwarts.edu",
    first_name="Severus",
    last_name="Snape",
    is_active=True,
    password=mkpasswd(),
)
user2.save()

user3 = User(
    email="hpotter@hogwarts.edu",
    first_name="Harry",
    last_name="Potter",
    is_active=True,
    password=mkpasswd(),
)
user3.save()

user4 = User(
    email="hgranger@hogwarts.edu",
    first_name="Hermione",
    last_name="Granger",
    is_active=True,
    password=mkpasswd(),
)
user4.save()

user5 = User(
    email="rweasley@hogwarts.edu",
    first_name="Ronald",
    last_name="Weasely",
    is_active=True,
    password=mkpasswd(),
)
user5.save()

class1 = Class(
    prefix="transfig",
    name="Transfiguration",
    droplet_image="ubuntu-20-04-x64",
    droplet_size="s-1vcpu-1gb",
    droplet_region="sfo3",
    droplet_student_limit=1,
)
class1.save()

class2 = Class(
    prefix="potions",
    name="Potions",
    droplet_image="ubuntu-20-04-x64",
    droplet_size="s-1vcpu-1gb",
    droplet_region="sfo3",
    droplet_student_limit=3,
    allow_registration=True,
)
class2.save()

teacher1 = Teacher(user=user1, droplet_limit=50)
teacher1.save()
teacher1.classes.add(class1)

teacher2 = Teacher(user=user2, droplet_limit=50)
teacher2.save()
teacher2.classes.add(class2)

student1 = Student(user=user3)
student1.save()
student1.classes.add(class1, class2)

student2 = Student(user=user4)
student2.save()
student2.classes.add(class1, class2)

student3 = Student(user=user5)
student3.save()
student3.classes.add(class1)

student4 = Student(user=user6)
student4.save()
student4.classes.add(class1)
