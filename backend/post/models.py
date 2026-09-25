from django.db import models
from account.models import Account

# Create your models here.
class BasePost(models.Model):
    class Locations(models.TextChoices):
        # --- 6 Special Municipalities (直轄市) ---
        TPE = 'TPE', '臺北市'
        NWT = 'NWT', '新北市'
        TYN = 'TYN', '桃園市'
        TXG = 'TXG', '臺中市'
        TNN = 'TNN', '臺南市 '
        KHH = 'KHH', '高雄市'
        # --- 3 Provincial Cities (市) ---
        KEE = 'KEE', '基隆市'
        HSZ = 'HSZ', '新竹市'
        CYI = 'CYI', '嘉義市'
        # --- 13 Counties (縣) ---
        HSQ = 'HSQ', '新竹縣'
        MIA = 'MIA', '苗栗縣'
        CHA = 'CHA', '彰化縣'
        NAN = 'NAN', '南投縣'
        YUN = 'YUN', '雲林縣'
        CYQ = 'CYQ', '嘉義縣'
        PIF = 'PIF', '屏東縣'
        ILA = 'ILA', '宜蘭縣'
        HUA = 'HUA', '花蓮縣'
        TTT = 'TTT', '臺東縣'
        PEN = 'PEN', '澎湖縣'
        KIN = 'KIN', '金門縣'
        LIE = 'LIE', '連江縣'
        OTH = 'OTH', '其他'
    
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='%(class)s_posts')
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    location = models.CharField(max_length=5, choices=Locations.choices, default=Locations.OTH)
    contact_info = models.CharField(max_length=200)
    shipping_methods = models.JSONField(default=list, help_text="List of shipping methods: ['localPickup', 'shipping']")
    image = models.URLField(blank=True, help_text="Cover photo URL")
    gallery = models.JSONField(default=list, help_text="All photo URLs, cover first")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True

class Species(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self):
        return self.name
    

class EquipmentPost(BasePost):
    class ConditionChoices(models.IntegerChoices):
        NOT_FUNCTIONAL = 0, 'Not Functional'
        USED = 1, 'Used'
        NEW = 2, 'New'
    
    condition = models.IntegerField(choices=ConditionChoices.choices, default=ConditionChoices.USED)
    
    class Meta:
        verbose_name = 'Equipment Post'
        verbose_name_plural = 'Equipment Posts'


class LiveAnimalPost(BasePost):
    class SexChoices(models.TextChoices):
        MALE = '1.0', 'Male (1.0)'
        FEMALE = '0.1', 'Female (0.1)'
        UNSEXED = 'unsexed', 'Unsexed'
    
    class LifeStageChoices(models.TextChoices):
        HATCHLING = 'hatchling', 'Hatchling'
        JUVENILE = 'juvenile', 'Juvenile'
        SUB_ADULT = 'subAdult', 'Sub-Adult'
        ADULT = 'adult', 'Adult'
    
    species = models.ForeignKey(Species, on_delete=models.CASCADE, related_name='live_posts')
    sex = models.CharField(max_length=20, choices=SexChoices.choices, default=SexChoices.UNSEXED)
    genetics = models.TextField(blank=True, help_text="Genetic traits separated by '/', e.g. 'Pastel/Pied'")
    life_stage = models.CharField(max_length=20, choices=LifeStageChoices.choices, default=LifeStageChoices.ADULT)
    age_years = models.FloatField(null=True, blank=True, help_text="Age in years")
    weight_grams = models.FloatField(null=True, blank=True, help_text="Weight in grams")
    size_cm = models.FloatField(null=True, blank=True, help_text="Size/Length in centimeters")
    diets = models.JSONField(default=list, help_text="List of diets: ['live', 'frozenThawed', 'pellets']")
    guide_notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Live Animal Post'
        verbose_name_plural = 'Live Animal Posts'


class ContactRequest(models.Model):
    """Records that a buyer sent their contact details to a seller, so a listing is only emailed once."""
    requester = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='contact_requests_sent')
    live_animal_post = models.ForeignKey(LiveAnimalPost, on_delete=models.CASCADE, null=True, blank=True, related_name='contact_requests')
    equipment_post = models.ForeignKey(EquipmentPost, on_delete=models.CASCADE, null=True, blank=True, related_name='contact_requests')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Contact Request'
        verbose_name_plural = 'Contact Requests'

    @property
    def post(self):
        return self.live_animal_post or self.equipment_post


class Report(models.Model):
    """Records a user flagging a listing for manual moderation review."""
    reporter = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='reports_filed')
    live_animal_post = models.ForeignKey(LiveAnimalPost, on_delete=models.CASCADE, null=True, blank=True, related_name='reports')
    equipment_post = models.ForeignKey(EquipmentPost, on_delete=models.CASCADE, null=True, blank=True, related_name='reports')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Report'
        verbose_name_plural = 'Reports'

    @property
    def post(self):
        return self.live_animal_post or self.equipment_post