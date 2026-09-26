"""
The species sellers choose from: common species in Taiwan's reptile hobby, each with the other names
people use for it (English common names, scientific names old and new, Chinese names). Typing any of
them in the listing editor picks the species, and marketplace search matches them (post/species.py).
Staff add more in the admin, and mapping a requested species adds its name as an alias.

The canonical names of the first seven are the ones listings already use. The frontend shows each
species under a translated label (Frontend/src/constants/species.js), keyed by the canonical name.
"""
import re

from django.db import migrations

CATALOG = {
    # Snakes
    'Ball Pythons': ['Ball Python', 'Royal Python', 'Python regius', '球蟒', '皇家蟒'],
    'Corn Snakes': ['Corn Snake', 'Red Rat Snake', 'Pantherophis guttatus', 'Elaphe guttata', '玉米蛇'],
    'Western Hognose Snakes': ['Western Hognose Snake', 'Western Hognose', 'Heterodon nasicus', '西部豬鼻蛇'],
    'California Kingsnakes': ['California Kingsnake', 'Cal King', 'Lampropeltis californiae', '加州王蛇'],
    'Milk Snakes': ['Milk Snake', 'Milksnake', 'Lampropeltis triangulum', '奶蛇'],
    'Boa Constrictors': ['Boa Constrictor', 'Red-tailed Boa', 'Boa imperator', '紅尾蚺'],
    'Carpet Pythons': ['Carpet Python', 'Morelia spilota', '地毯蟒'],
    'Green Tree Pythons': ['Green Tree Python', 'GTP', 'Morelia viridis', '綠樹蟒'],
    'Blood Pythons': ['Blood Python', 'Python brongersmai', '血蟒'],
    'Rosy Boas': ['Rosy Boa', 'Lichanura trivirgata', '玫瑰蚺'],
    'Kenyan Sand Boas': ['Kenyan Sand Boa', 'Eryx colubrinus', '肯亞沙蚺'],
    # Lizards
    'Leopard Geckos': ['Leopard Gecko', 'Eublepharis macularius', '豹紋守宮', '豹紋壁虎'],
    'Crested Geckos': ['Crested Gecko', 'Crestie', 'Correlophus ciliatus', 'Rhacodactylus ciliatus', '睫角守宮'],
    'Gargoyle Geckos': ['Gargoyle Gecko', 'Rhacodactylus auriculatus', '石獅守宮'],
    'African Fat-tailed Geckos': ['African Fat-tailed Gecko', 'Fat-tailed Gecko', 'Hemitheconyx caudicinctus', '肥尾守宮'],
    'Tokay Geckos': ['Tokay Gecko', 'Gekko gecko', '大壁虎', '蛤蚧'],
    'New Caledonian Giant Geckos': ['New Caledonian Giant Gecko', 'Leachianus Gecko', 'Leachie', 'Rhacodactylus leachianus', '巨人守宮'],
    'Bearded Dragons': ['Bearded Dragon', 'Central Bearded Dragon', 'Beardie', 'Pogona vitticeps', '鬃獅蜥'],
    'Blue-tongued Skinks': ['Blue-tongued Skink', 'Blue Tongue Skink', 'Blue Tongue Skinks', 'Bluey', 'Tiliqua', '藍舌蜥', '藍舌石龍子'],
    'Veiled Chameleons': ['Veiled Chameleon', 'Yemen Chameleon', 'Chamaeleo calyptratus', '高冠變色龍', '葉門變色龍'],
    'Panther Chameleons': ['Panther Chameleon', 'Furcifer pardalis', '七彩變色龍', '豹紋變色龍'],
    'Argentine Tegus': ['Argentine Tegu', 'Argentine Black and White Tegu', 'Black and White Tegu', 'Salvator merianae', 'Tupinambis merianae', '阿根廷黑白泰加蜥', '黑白泰加蜥'],
    'Savannah Monitors': ['Savannah Monitor', 'Varanus exanthematicus', '草原巨蜥'],
    'Uromastyx': ['Spiny-tailed Lizard', 'Spiny-tailed Lizards', '王者蜥', '刺尾蜥'],
    # Turtles and tortoises
    '紅面蛋': ['Red-cheeked Mud Turtles', 'Red-cheeked Mud Turtle', 'Kinosternon scorpioides cruentatum', '紅面蛋龜'],
    '鑽紋龜': ['Diamondback Terrapins', 'Diamondback Terrapin', 'Malaclemys terrapin'],
    'Common Musk Turtles': ['Common Musk Turtle', 'Stinkpot', 'Sternotherus odoratus', '麝香龜'],
    'Sulcata Tortoises': ['Sulcata Tortoise', 'African Spurred Tortoise', 'Centrochelys sulcata', 'Geochelone sulcata', '蘇卡達象龜', '蘇卡達陸龜', '蘇卡達'],
    'Russian Tortoises': ['Russian Tortoise', "Horsfield's Tortoise", 'Testudo horsfieldii', 'Agrionemys horsfieldii', '四爪陸龜', '俄羅斯陸龜'],
    "Hermann's Tortoises": ["Hermann's Tortoise", 'Testudo hermanni', '赫曼陸龜'],
    'Leopard Tortoises': ['Leopard Tortoise', 'Stigmochelys pardalis', 'Geochelone pardalis', '豹紋陸龜', '豹龜'],
}


def normalize(name):
    # A copy of post.species.normalize: migrations shouldn't import app code that may change later.
    return re.sub(r'[\W_]+', '', name.casefold())


def seed_catalog(apps, schema_editor):
    Species = apps.get_model('post', 'Species')
    SpeciesAlias = apps.get_model('post', 'SpeciesAlias')
    taken = {normalize(name) for name in Species.objects.values_list('name', flat=True)}
    taken |= {normalize(name) for name in SpeciesAlias.objects.values_list('name', flat=True)}
    for name, aliases in CATALOG.items():
        # Existing databases may already have the species (from sample or demo listings), even twice.
        species = Species.objects.filter(name=name).order_by('id').first()
        if species is None:
            if normalize(name) in taken:
                continue  # already listed under another name; leave that to staff
            species = Species.objects.create(name=name)
            taken.add(normalize(name))
        for alias in aliases:
            # Skip names that already pick a species, so an alias never makes a name ambiguous.
            if normalize(alias) not in taken:
                SpeciesAlias.objects.create(species=species, name=alias)
                taken.add(normalize(alias))


class Migration(migrations.Migration):

    dependencies = [
        ('post', '0017_species_review'),
    ]

    operations = [
        migrations.RunPython(seed_catalog, migrations.RunPython.noop),
    ]
