"""
Seed the database with realistic demo accounts (sellers + buyers), listings and activity.

    python manage.py seed_demo            # create demo data (refuses if it already exists)
    python manage.py seed_demo --reset    # delete previous demo data first, then recreate
    python manage.py seed_demo --delete   # only delete demo data

Demo accounts are identified by their email domain (DEMO_EMAIL_DOMAIN), so --reset/--delete never
touch real accounts. Output is deterministic for a given --seed.
"""
import random
from datetime import timedelta
from decimal import Decimal
import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from account.models import Account, Review
from account.reviews import refresh_rating
from auction import orders
from auction.models import Auction, Bid, Deposit, Order
from auction.services import deposit_amount_for
from account.models import Review
from account.reviews import refresh_rating
from post.models import ContactRequest, EquipmentPost, LiveAnimalPost, Report, Species

DEMO_EMAIL_DOMAIN = 'demo.morphmarket.test'
DEMO_PASSWORD = 'DemoPass123!'

# Freely licensed photos from Wikimedia Commons, checked by hand to show the right species.
PHOTOS = {
    'Ball Pythons': [
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/e/e5/Python-regius-kopf-k%C3%B6nigspython.jpg/960px-Python-regius-kopf-k%C3%B6nigspython.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/f/ff/Ball_Python_%28Python_regius%29.jpg/960px-Ball_Python_%28Python_regius%29.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/3/3a/Female_Ball_python_%28Python_regius%29.jpg/960px-Female_Ball_python_%28Python_regius%29.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/2/24/Ball_python_%28Python_regius%29%2C_Bronx_Zoo.jpg/960px-Ball_python_%28Python_regius%29%2C_Bronx_Zoo.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/4/46/Python_regius_-_ball_python.jpg/960px-Python_regius_-_ball_python.jpg',
    ],
    'Crested Geckos': [
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/3/3c/Correlophus_ciliatus_33606417.jpg/960px-Correlophus_ciliatus_33606417.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/f/f6/Correlophus_ciliatus_33605230.jpg/960px-Correlophus_ciliatus_33605230.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/4/44/Correlophus_ciliatus_33484989.jpg/960px-Correlophus_ciliatus_33484989.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/7/71/Correlophus_ciliatus_34354132.jpg/960px-Correlophus_ciliatus_34354132.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/2/2c/Correlophus_ciliatus_33605448.jpg/960px-Correlophus_ciliatus_33605448.jpg',
    ],
    'Leopard Geckos': [
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/b/bc/Leopard_gecko_%28Eublepharis_macularius%29%2C_Entomica_2.jpg/960px-Leopard_gecko_%28Eublepharis_macularius%29%2C_Entomica_2.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/7/7f/Eublepharis_macularius_2009_G6.jpg/960px-Eublepharis_macularius_2009_G6.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/9/99/Eublepharis_macularius_2009_G5.jpg/960px-Eublepharis_macularius_2009_G5.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/4/43/Eublepharis_macularius_2009_G8.jpg/960px-Eublepharis_macularius_2009_G8.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/0/0d/Eublepharis_macularius_2009_G7.jpg/960px-Eublepharis_macularius_2009_G7.jpg',
    ],
    'Corn Snakes': [
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/0/01/Pantherophis_guttatus_Head.jpg/960px-Pantherophis_guttatus_Head.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/d/d9/Corn_Snake_opal.jpg/960px-Corn_Snake_opal.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/b/bd/Pantherophis_guttatus-020.jpg/960px-Pantherophis_guttatus-020.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/8/84/Cornsnake_%28Pantherophis_guttatus%29_-_Flickr_-_2ndPeter.jpg/960px-Cornsnake_%28Pantherophis_guttatus%29_-_Flickr_-_2ndPeter.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/6/6f/Corn_Snake_-_Pantherophis_guttatus%2C_Sapelo_Island%2C_Georgia.jpg/960px-Corn_Snake_-_Pantherophis_guttatus%2C_Sapelo_Island%2C_Georgia.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/f/fb/Pantherophis_guttatus_%2848325672551%29.jpg/960px-Pantherophis_guttatus_%2848325672551%29.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/b/b2/Kopfprofil_Pantherophis_guttatus.jpg/960px-Kopfprofil_Pantherophis_guttatus.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/c/c6/Kornnatter.jpg/960px-Kornnatter.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/8/8e/Kornnatter_%28Pantherophis_guttatus%29%2C_Seitenansicht.jpg/960px-Kornnatter_%28Pantherophis_guttatus%29%2C_Seitenansicht.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/a/a5/Corn_Snake_-_Pantherophis_guttatus%2C_Sapelo_Island%2C_Georgia_-_16880785352.jpg/960px-Corn_Snake_-_Pantherophis_guttatus%2C_Sapelo_Island%2C_Georgia_-_16880785352.jpg',
        'https://upload.wikimedia.org/wikipedia/commons/2/2a/Pantherophis_guttatus_eiablage.jpg',
    ],
    'Bearded Dragons': [
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/2/20/Osnabr%C3%BCck_-_Zoo_-_Pogona_vitticeps_01.jpg/960px-Osnabr%C3%BCck_-_Zoo_-_Pogona_vitticeps_01.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/2/2f/383_-_Head_of_central_bearded_dragon_%28Pogona_vitticeps%29.jpg/960px-383_-_Head_of_central_bearded_dragon_%28Pogona_vitticeps%29.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/3/34/Pogona_vitticeps_2009_G2.jpg/960px-Pogona_vitticeps_2009_G2.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/a/a7/Pogona_vitticeps_2009_G4.jpg/960px-Pogona_vitticeps_2009_G4.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/3/3a/Pogona_vitticeps_2009_G1.jpg/960px-Pogona_vitticeps_2009_G1.jpg',
    ],
    '紅面蛋': [
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/2/26/Kinosternon_scorpioides_scorpioides_64675726.jpg/960px-Kinosternon_scorpioides_scorpioides_64675726.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/9/92/Kinosternon_scorpioides_scorpioides_64675451.jpg/960px-Kinosternon_scorpioides_scorpioides_64675451.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/6/65/Kinosternon_scorpioides_ssp._albogulare.jpg/960px-Kinosternon_scorpioides_ssp._albogulare.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/6/63/Kinosternon_scorpioides_Scorpion_Mud_Turtle%2C_Tamaulipas.jpg/960px-Kinosternon_scorpioides_Scorpion_Mud_Turtle%2C_Tamaulipas.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/7/79/Kinosternon_scorpioides_243336409.jpg/960px-Kinosternon_scorpioides_243336409.jpg',
    ],
    '鑽紋龜': [
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/b/b9/Malaclemys_terrapin_ssp._terrapin.jpg/960px-Malaclemys_terrapin_ssp._terrapin.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/9/9d/Malaclemys_terrapin_diamondback_terrapin_turtle_animal.jpg/960px-Malaclemys_terrapin_diamondback_terrapin_turtle_animal.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/a/af/Diamond_terrapin_turtle_reptile_malaclemys_terrapin.jpg/960px-Diamond_terrapin_turtle_reptile_malaclemys_terrapin.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/1/14/Malaclemys_terrapin_%28diamondback_terrapin%29_2_%2815101239604%29.jpg/960px-Malaclemys_terrapin_%28diamondback_terrapin%29_2_%2815101239604%29.jpg',
        'https://thumb.wikimedia.org/wikipedia/commons/thumb/b/b3/Malaclemys_terrapin_%28diamondback_terrapin%29_1_%2815697462306%29.jpg/960px-Malaclemys_terrapin_%28diamondback_terrapin%29_1_%2815697462306%29.jpg',
    ],
}

# Per-species listing templates. Ranges are (min, max); stages map to (age years, weight g, length cm).
SPECIES = {
    'Ball Pythons': {
        'title': '{traits} Ball Python',
        'normal': 'Normal',
        'traits': ['Pastel', 'Pied', 'Enchi', 'Clown', 'Banana', 'Mojave', 'Lesser', 'Yellow Belly', 'Cinnamon', 'Fire', 'Het Clown', 'Het Pied'],
        'price': (1500, 38000),
        'diets': [['frozenThawed'], ['live'], ['live', 'frozenThawed']],
        'stages': {
            'hatchling': ((0.1, 0.4), (60, 150), (35, 50)),
            'juvenile': ((0.5, 1.5), (200, 700), (60, 90)),
            'subAdult': ((1.5, 2.5), (800, 1200), (90, 110)),
            'adult': ((3, 8), (1300, 2200), (110, 150)),
        },
        'care': 'Kept at 31°C hot spot / 26°C cool side, 60% humidity. Feeding every 7-10 days.',
    },
    'Crested Geckos': {
        'title': '{traits} Crested Gecko',
        'normal': 'Wild Type',
        'traits': ['Lilly White', 'Harlequin', 'Extreme Harlequin', 'Dalmatian', 'Pinstripe', 'Tiger', 'Flame', 'Cappuccino', 'Red'],
        'price': (2500, 16000),
        'diets': [['pellets'], ['pellets', 'live']],
        'stages': {
            'hatchling': ((0.1, 0.3), (1, 3), (6, 9)),
            'juvenile': ((0.3, 0.8), (5, 15), (10, 14)),
            'subAdult': ((0.8, 1.5), (18, 30), (15, 18)),
            'adult': ((1.5, 6), (35, 55), (18, 22)),
        },
        'care': 'Room temperature 22-26°C, misted nightly. Eating Pangea / Repashy plus weekly crickets.',
    },
    'Leopard Geckos': {
        'title': '{traits} Leopard Gecko',
        'normal': 'Normal',
        'traits': ['Mack Snow', 'Tremper Albino', 'Tangerine', 'Bell Albino', 'Eclipse', 'Blizzard', 'Super Hypo', 'Carrot Tail', 'Bold Stripe'],
        'price': (1200, 9000),
        'diets': [['live']],
        'stages': {
            'hatchling': ((0.1, 0.3), (3, 6), (8, 10)),
            'juvenile': ((0.3, 0.8), (10, 30), (12, 16)),
            'subAdult': ((0.8, 1.2), (35, 50), (17, 20)),
            'adult': ((1.2, 8), (55, 90), (20, 25)),
        },
        'care': 'Belly heat 32°C, dry hide + moist hide. Feeding dubia roaches and mealworms, dusted with calcium.',
    },
    'Corn Snakes': {
        'title': '{traits} Corn Snake',
        'normal': 'Normal',
        'traits': ['Amel', 'Anery', 'Snow', 'Hypo', 'Tessera', 'Motley', 'Okeetee', 'Lavender', 'Het Amel'],
        'price': (1500, 6000),
        'diets': [['frozenThawed']],
        'stages': {
            'hatchling': ((0.1, 0.3), (6, 12), (25, 35)),
            'juvenile': ((0.4, 1), (25, 80), (45, 70)),
            'subAdult': ((1, 2), (100, 250), (75, 100)),
            'adult': ((2, 10), (300, 700), (110, 150)),
        },
        'care': 'Hot spot 29°C, secure lid (escape artists!). Taking frozen/thawed mice every 7-14 days.',
    },
    'Bearded Dragons': {
        'title': '{traits} Bearded Dragon',
        'normal': 'Normal',
        'traits': ['Hypo', 'Trans', 'Leatherback', 'Dunner', 'Citrus', 'Red', 'Zero', 'Het Hypo'],
        'price': (3000, 15000),
        'diets': [['live'], ['live', 'pellets']],
        'stages': {
            'hatchling': ((0.1, 0.3), (5, 15), (10, 15)),
            'juvenile': ((0.3, 0.8), (40, 150), (20, 35)),
            'subAdult': ((0.8, 1.5), (200, 350), (35, 45)),
            'adult': ((1.5, 10), (380, 550), (45, 55)),
        },
        'care': 'Basking 40°C with T5 HO UVB. Daily greens plus dubia / black soldier fly larvae.',
    },
    '紅面蛋': {
        'title': '{traits} 紅面蛋龜 Red-cheeked Mud Turtle',
        'normal': '',
        'traits': ['Captive Bred', 'High Red', 'Pair'],
        'price': (800, 4500),
        'diets': [['pellets'], ['pellets', 'live']],
        'stages': {
            'hatchling': ((0.1, 0.4), (5, 12), (3, 4)),
            'juvenile': ((0.5, 1.5), (30, 120), (5, 8)),
            'subAdult': ((1.5, 3), (150, 300), (9, 11)),
            'adult': ((3, 15), (320, 600), (12, 16)),
        },
        'care': 'Shallow water 25-27°C with a dry basking area. Eats turtle pellets, shrimp and snails.',
    },
    '鑽紋龜': {
        'title': '{traits} 鑽紋龜 Diamondback Terrapin',
        'normal': '',
        'traits': ['Captive Bred', 'Northern', 'Ornate', 'High Contrast'],
        'price': (6000, 22000),
        'diets': [['pellets'], ['pellets', 'live']],
        'stages': {
            'hatchling': ((0.1, 0.4), (8, 15), (3, 4)),
            'juvenile': ((0.5, 1.5), (40, 150), (6, 9)),
            'subAdult': ((1.5, 3), (180, 350), (10, 13)),
            'adult': ((3, 15), (400, 900), (13, 20)),
        },
        'care': 'Brackish water (SG 1.010), 26°C, strong UVB. Eats pellets, shrimp, clams and small fish.',
    },
}

DESCRIPTIONS = [
    'Healthy, alert and eating well. Captive bred by us, no health issues. Photos are of the actual animal.',
    'Great feeder, easy to handle and very calm. Selling to make room for this season\'s clutch.',
    'Beautiful colours that keep improving with each shed. Fully established and ready for a new home.',
    'From proven lines with clean genetics. Happy to send more photos or a video on request.',
    'Well started and handled regularly. Comes with feeding records and a care sheet.',
    '個體健康活潑，進食穩定。歡迎私訊詢問更多照片。',
]

EQUIPMENT = [
    ('Exo Terra 60×45×60 Glass Terrarium', 'Front-opening glass terrarium, lockable doors, mesh top. No scratches.', (2500, 5500), 'enclosure'),
    ('Arcadia T5 HO 12% UVB Kit (54W)', 'Full kit with reflector and controller. Tube has ~4 months of use.', (1800, 3200), 'lighting'),
    ('Inkbird ITC-308 Thermostat', 'Dual relay thermostat for heat mats and ceramic heaters. Works perfectly.', (600, 1200), 'climate'),
    ('Zoo Med ReptiTherm Heat Mat (Large)', 'Under-tank heater, only used for one season.', (400, 800), 'heating'),
    ('PVC Snake Rack — 6 tubs', 'Heat-taped rack with 6 × 32qt tubs, includes thermostat. Pickup only.', (5000, 9000), 'enclosure'),
    ('Ceramic Heat Emitter 100W + Dome', 'Includes guarded dome fixture. Great for night-time heat.', (350, 700), 'heating'),
    ('Crested Gecko Bioactive Starter Set', 'Substrate, springtails, isopods, cork bark and live pothos.', (900, 1800), 'substrateDecor'),
    ('Turtle Basking Platform + Filter Combo', 'Floating basking dock plus internal filter for 60-90cm tanks.', (700, 1500), 'other'),
    ('Digital Thermometer / Hygrometer ×3', 'Three probes, new batteries.', (200, 450), 'climate'),
    ('Reptile Carrier Box (Ventilated)', 'Clear ventilated carrier, perfect for expos and vet visits.', (250, 500), 'transport'),
]

# Demo review comments: [for 1-3 stars, for 4-5 stars].
REVIEW_COMMENTS = {
    False: ['Animal was fine but replies were slow.', '交貨延遲了幾天，不過個體沒問題。', 'Smaller than the photos suggested.'],
    True: ['Healthy animal, careful packing, would buy again.', '個體健康，賣家很有耐心回答問題！', 'Exactly as described. Great communication.', 'Smooth pickup, very knowledgeable breeder.'],
}

# username, display name (first, last), account setup, home location, what they list.
SELLERS = [
    dict(username='apex_exotics', first_name='Apex', last_name='Exotics', account_type='commercial', paid=True,
         verified=True, rating=4.9, location='TPE', line_id='apexexotics',
         bio='Taipei ball python and corn snake breeder since 2014. Shipping island-wide with live arrival guarantee.',
         animals={'Ball Pythons': 8, 'Corn Snakes': 3}, equipment=4),
    dict(username='highridge_geckos', first_name='High Ridge', last_name='Geckos', account_type='commercial', paid=True,
         verified=True, rating=4.8, location='NWT', line_id='highridgegecko',
         bio='Small-batch crested and leopard gecko projects focused on Lilly White and Harlequin lines.',
         animals={'Crested Geckos': 7, 'Leopard Geckos': 3}, equipment=2),
    dict(username='morph_kingdom', first_name='Morph', last_name='Kingdom', account_type='commercial', paid=False,
         verified=True, rating=4.6, location='TXG', line_id='morphkingdom',
         bio='Mixed collection in Taichung — pythons, geckos, corns and beardies.',
         animals={'Ball Pythons': 4, 'Leopard Geckos': 4, 'Corn Snakes': 3, 'Bearded Dragons': 3}, equipment=2),
    dict(username='dragon_den_tw', first_name='Dragon', last_name='Den', account_type='commercial', paid=False,
         verified=False, rating=4.2, location='KHH', line_id='dragonden',
         bio='Bearded dragon specialists in Kaohsiung. Hypo and Leatherback projects.',
         animals={'Bearded Dragons': 5, 'Leopard Geckos': 2}, equipment=3),
    dict(username='shell_and_scale', first_name='Shell', last_name='& Scale', account_type='commercial', paid=False,
         verified=False, rating=3.7, location='TNN', line_id='shellscale',
         bio='Tainan turtle keepers. Captive-bred mud turtles and terrapins only.',
         animals={'紅面蛋': 4, '鑽紋龜': 3}, equipment=0),
    dict(username='mei_lin', first_name='美', last_name='林', account_type='hobbyist', paid=False,
         verified=False, rating=0.0, location='TYN', line_id='meilin_gecko',
         bio='', animals={'Crested Geckos': 3, 'Leopard Geckos': 2}, equipment=0),  # exactly at the 5-post hobbyist cap
    dict(username='kevin_chen', first_name='Kevin', last_name='Chen', account_type='hobbyist', paid=False,
         verified=False, rating=0.0, location='HSZ', line_id='',
         bio='', animals={'Ball Pythons': 2, 'Corn Snakes': 1}, equipment=0),
    dict(username='tina_turtles', first_name='Tina', last_name='Wang', account_type='hobbyist', paid=False,
         verified=False, rating=0.0, location='ILA', line_id='tinaturtle',
         bio='', animals={'紅面蛋': 1, '鑽紋龜': 1}, equipment=0),
    dict(username='jay_wu', first_name='Jay', last_name='Wu', account_type='hobbyist', paid=False,
         verified=False, rating=0.0, location='HUA', line_id='',
         bio='', animals={'Bearded Dragons': 1}, equipment=1),
]

BUYERS = [
    dict(username='buyer_amy', first_name='Amy', last_name='Liu', location='TPE'),
    dict(username='buyer_jason', first_name='Jason', last_name='Huang', location='KHH'),
    dict(username='buyer_hsu', first_name='俊宏', last_name='許', location='TXG'),
    dict(username='new_user_sam', first_name='Sam', last_name='Lee', location='OTH'),  # no activity at all
]

ALL_LOCATIONS = [code for code, _ in LiveAnimalPost.Locations.choices]

# Auctions on the paid sellers' animals, relative to now: when each ends (negative = already ended),
# how many bids it has, whether the seller offers buy-now (at the listing's price), and optionally when
# it starts (upcoming auctions). Covers every state the auction pages show: ending in minutes, running,
# with and without buy-now, no bids yet, not started, ended with and without a winner.
AUCTION_PLANS = [
    dict(ends_in_hours=0.4, bids=5),
    dict(ends_in_hours=3, bids=2, buy_now=True),
    dict(ends_in_hours=20, bids=7),
    dict(ends_in_hours=52, bids=0, buy_now=True),
    dict(ends_in_hours=100, bids=3, buy_now=True),
    dict(ends_in_hours=170, bids=1),
    dict(ends_in_hours=90, bids=0, starts_in_hours=18, buy_now=True),
    dict(ends_in_hours=-10, bids=4),                 # winner still has to pay the rest
    dict(ends_in_hours=-30, bids=3, winner_paid=True),  # paid: the seller has to hand it over
    dict(ends_in_hours=-40, bids=0),
]


class Command(BaseCommand):
    help = 'Create demo sellers, buyers, listings, contact requests and reports for local testing.'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Delete existing demo data before seeding.')
        parser.add_argument('--delete', action='store_true', help='Delete existing demo data and exit.')
        parser.add_argument('--seed', type=int, default=42, help='Random seed (default 42).')

    def handle(self, *args, **options):
        demo_accounts = Account.objects.filter(email__endswith=f'@{DEMO_EMAIL_DOMAIN}')

        if options['reset'] or options['delete']:
            count = demo_accounts.count()
            demo_accounts.delete()  # cascades to their posts, contact requests, reports and auctions
            self.stdout.write(f'Deleted {count} demo accounts and everything they owned.')
            if options['delete']:
                return
        elif demo_accounts.exists():
            raise CommandError('Demo data already exists. Re-run with --reset to recreate it.')

        self.rng = random.Random(options['seed'])
        self.now = timezone.now()
        with transaction.atomic():
            species = {name: Species.objects.get_or_create(name=name)[0] for name in SPECIES}
            sellers = [self.create_seller(spec, species) for spec in SELLERS]
            buyers = [self.create_account(spec) for spec in BUYERS]
            self.create_activity(buyers[:-1], sellers)
            self.create_auctions(buyers[:-1] + sellers[2:4], sellers)

        self.print_summary()

    # --- accounts -------------------------------------------------------------------------------

    def create_account(self, spec, **extra):
        return Account.objects.create_user(
            username=spec['username'],
            email=f"{spec['username']}@{DEMO_EMAIL_DOMAIN}",
            password=DEMO_PASSWORD,
            first_name=spec['first_name'],
            last_name=spec['last_name'],
            phone_number=f'09{self.rng.randint(10, 99)}-{self.rng.randint(100, 999)}-{self.rng.randint(100, 999)}',
            **extra,
        )

    def create_seller(self, spec, species):
        is_commercial = spec['account_type'] == 'commercial'
        seller = self.create_account(
            spec,
            account_type=spec['account_type'],
            is_paid_account=spec['paid'],
            verified_seller=spec['verified'],
            bio=spec['bio'] or None,
            line_id=spec['line_id'] or None,
        )
        # The rating the demo reviews for this seller should average around (see create_reviews).
        seller.demo_rating = spec['rating']
        planned = sum(spec['animals'].values()) + spec['equipment']
        assert planned <= seller.max_post_count, f"{seller.username} would exceed its post limit"

        for species_name, count in spec['animals'].items():
            for _ in range(count):
                self.create_animal_post(seller, species[species_name], spec['location'])
        for _ in range(spec['equipment']):
            self.create_equipment_post(seller, spec['location'])
        return seller

    # --- listings -------------------------------------------------------------------------------

    def contact_info(self, seller):
        info = {'phone': seller.phone_number, 'email': seller.email}
        if seller.line_id:
            info['line'] = seller.line_id
        if seller.is_commercial:
            info['instagram'] = f'@{seller.username}'
        return json.dumps(info)

    def pick_location(self, home):
        # Most sellers list from home; some list from wherever they'll meet buyers.
        return home if self.rng.random() < 0.75 else self.rng.choice(ALL_LOCATIONS)

    def backdate(self, post):
        created = self.now - timedelta(days=self.rng.randint(0, 90), hours=self.rng.randint(0, 23))
        type(post).objects.filter(pk=post.pk).update(created_at=created, updated_at=created)

    def create_animal_post(self, seller, species, home):
        template = SPECIES[species.name]
        rng = self.rng

        trait_count = rng.choices([0, 1, 2, 3], weights=[2, 4, 3, 1])[0]
        traits = rng.sample(template['traits'], trait_count)
        trait_label = ' '.join(traits) or template['normal']
        title = template['title'].format(traits=trait_label).strip()

        stage = rng.choices(list(template['stages']), weights=[3, 4, 2, 3])[0]
        (age_lo, age_hi), (w_lo, w_hi), (s_lo, s_hi) = template['stages'][stage]
        sex = 'unsexed' if stage == 'hatchling' and rng.random() < 0.7 else rng.choice(['1.0', '0.1'])

        lo, hi = template['price']
        price = lo + (hi - lo) * (0.15 + 0.25 * trait_count) * rng.uniform(0.6, 1.2)
        price = Decimal(max(lo, min(hi, round(price, -2))))

        photos = PHOTOS[species.name]
        max_gallery = seller.max_images_per_post - 1  # the cover counts as one image
        gallery_size = rng.randint(1, min(max_gallery, 4, len(photos)))
        gallery = rng.sample(photos, gallery_size)

        post = LiveAnimalPost.objects.create(
            account=seller,
            species=species,
            title=title[:200],
            description=rng.choice(DESCRIPTIONS),
            price=price,
            location=self.pick_location(home),
            contact_info=self.contact_info(seller),
            shipping_methods=rng.choice([['localPickup'], ['shipping'], ['localPickup', 'shipping']]),
            sex=sex,
            genetics='/'.join(traits),
            life_stage=stage,
            age_years=round(rng.uniform(age_lo, age_hi), 1),
            weight_grams=round(rng.uniform(w_lo, w_hi), 1),
            size_cm=round(rng.uniform(s_lo, s_hi), 1),
            diets=rng.choice(template['diets']),
            image=gallery[0],
            gallery=gallery,
            guide_notes=template['care'],
        )
        self.backdate(post)
        return post

    def create_equipment_post(self, seller, home):
        title, description, (lo, hi), category = self.rng.choice(EQUIPMENT)
        condition = self.rng.choices([0, 1, 2], weights=[1, 6, 3])[0]
        post = EquipmentPost.objects.create(
            account=seller,
            title=title,
            description=description,
            price=Decimal(round(self.rng.uniform(lo, hi), -1)),
            location=self.pick_location(home),
            contact_info=self.contact_info(seller),
            shipping_methods=self.rng.choice([['localPickup'], ['localPickup', 'shipping']]),
            condition=condition,
            category=category,
        )
        self.backdate(post)
        return post

    # --- activity -------------------------------------------------------------------------------

    def create_activity(self, buyers, sellers):
        live_posts = list(LiveAnimalPost.objects.filter(account__in=sellers))
        for buyer in buyers:
            for post in self.rng.sample(live_posts, 5):
                ContactRequest.objects.create(requester=buyer, live_animal_post=post)
        # A seller asking another seller about an animal is realistic too.
        ContactRequest.objects.create(
            requester=sellers[1], live_animal_post=next(p for p in live_posts if p.account_id == sellers[0].id),
        )
        for reporter, post in zip(buyers, self.rng.sample(live_posts, len(buyers))):
            Report.objects.create(reporter=reporter, live_animal_post=post)
        self.create_reviews(sellers)

    def create_reviews(self, sellers):
        # Real reviews from buyers who contacted a seller, so seller_rating and total_reviews come from
        # account.reviews like they do on the site, around each seller's demo rating.
        by_id = {seller.id: seller for seller in sellers}
        pairs = set(ContactRequest.objects.filter(live_animal_post__account__in=sellers).values_list(
            'requester_id', 'live_animal_post__account_id',
        ))
        for requester_id, seller_id in sorted(pairs):
            seller = by_id[seller_id]
            if requester_id == seller_id or not seller.demo_rating:
                continue
            rating = max(1, min(5, round(self.rng.gauss(seller.demo_rating, 0.6))))
            Review.objects.create(
                seller=seller, reviewer_id=requester_id, rating=rating,
                comment=self.rng.choice(REVIEW_COMMENTS[rating >= 4]),
            )
        for seller in sellers:
            refresh_rating(seller)

    # --- auctions -------------------------------------------------------------------------------

    def create_auctions(self, bidders, sellers):
        # Built directly rather than through auction.services so start/end and bid times can be in
        # the past. Deposits use a 'demo' provider so they're recognisable in the admin.
        auction_sellers = [seller for seller in sellers if seller.can_start_auction]
        posts = list(LiveAnimalPost.objects.filter(account__in=auction_sellers).order_by('id'))
        for post, plan in zip(self.rng.sample(posts, len(AUCTION_PLANS)), AUCTION_PLANS):
            self.create_auction(post, bidders, **plan)

    def create_auction(self, post, bidders, ends_in_hours, bids, starts_in_hours=None, buy_now=False, winner_paid=False):
        rng = self.rng
        ends_at = self.now + timedelta(hours=ends_in_hours)
        if starts_in_hours is None:
            starts_at = min(self.now, ends_at) - timedelta(days=rng.randint(2, 5), hours=rng.randint(0, 23))
        else:
            starts_at = self.now + timedelta(hours=starts_in_hours)
        starting_price = max(Decimal(500), (post.price * Decimal('0.6') / 100).quantize(Decimal(1)) * 100)
        increment = Decimal(100) if starting_price < 10000 else Decimal(500)
        # The listing's price is well above the starting price (60% of it), so it's a sensible buy-now price.
        buy_now_price = post.price if buy_now else None

        auction = Auction.objects.create(
            seller=post.account, live_animal_post=post, starting_price=starting_price,
            min_increment=increment, buy_now_price=buy_now_price, deposit_amount=deposit_amount_for(starting_price),
            currency=settings.AUCTION_CURRENCY, starts_at=starts_at, ends_at=ends_at,
        )

        amount = starting_price
        bid_window = (min(self.now, ends_at) - starts_at).total_seconds()
        bid_times = sorted(starts_at + timedelta(seconds=rng.uniform(0, bid_window)) for _ in range(bids))
        bidder = None
        for bid_time in bid_times:
            bidder = rng.choice([candidate for candidate in bidders if candidate != bidder])
            deposit, _ = Deposit.objects.get_or_create(
                auction=auction, account=bidder,
                defaults=dict(amount=auction.deposit_amount, currency=auction.currency,
                              status=Deposit.Status.HELD, provider='demo'),
            )
            bid = Bid.objects.create(auction=auction, bidder=bidder, amount=amount, deposit=deposit)
            Bid.objects.filter(pk=bid.pk).update(created_at=bid_time)
            amount += increment * rng.choice([1, 1, 2, 3])

        if ends_at <= self.now:
            auction.status = Auction.Status.ENDED
            auction.winning_bid = auction.highest_bid
            auction.save(update_fields=['status', 'winning_bid'])
            auction.deposits.exclude(account=bidder).update(status=Deposit.Status.RELEASED)
            if auction.winning_bid:
                order = orders.create_bid_order(auction, auction.winning_bid)
                if winner_paid:
                    order.deposit.status = Deposit.Status.CAPTURED
                    order.deposit.save(update_fields=['status'])
                    order.status, order.balance_status = Order.Status.PAID, Order.BalanceStatus.PAID
                    order.paid_at = self.now - timedelta(hours=6)
                    order.handover_due_at = order.paid_at + timedelta(days=settings.ORDER_HANDOVER_DAYS)
                    order.save()
        return auction

    def print_summary(self):
        accounts = Account.objects.filter(email__endswith=f'@{DEMO_EMAIL_DOMAIN}').order_by('id')
        self.stdout.write(self.style.SUCCESS(
            f'\nSeeded {accounts.count()} accounts, '
            f'{LiveAnimalPost.objects.filter(account__in=accounts).count()} animal listings, '
            f'{EquipmentPost.objects.filter(account__in=accounts).count()} equipment listings, '
            f'{ContactRequest.objects.filter(requester__in=accounts).count()} contact requests, '
            f'{Report.objects.filter(reporter__in=accounts).count()} reports, '
            f'{Auction.objects.filter(seller__in=accounts).count()} auctions.\n'
        ))
        self.stdout.write(f'All demo accounts use the password: {DEMO_PASSWORD}\n')
        self.stdout.write(f"{'username':<18} {'role':<22} {'posts':>5}")
        for account in accounts:
            posts = account.liveanimalpost_posts.count() + account.equipmentpost_posts.count()
            if posts == 0:
                role = 'buyer'
            elif account.is_commercial:
                role = 'commercial' + (' (paid)' if account.is_paid_account else '') + (' ✓' if account.verified_seller else '')
            else:
                role = 'hobbyist seller'
            self.stdout.write(f'{account.username:<18} {role:<22} {posts:>3}/{account.max_post_count}')
