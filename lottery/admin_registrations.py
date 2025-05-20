from .admin_site import lottery_admin_site
from .models import LotteryType, LotteryDraw, PrizeCategory
from .admin import LotteryTypeAdmin, LotteryDrawAdmin, PrizeCategoryAdmin

# Register models with the admin site
lottery_admin_site.register(LotteryType, LotteryTypeAdmin)
lottery_admin_site.register(LotteryDraw, LotteryDrawAdmin)
lottery_admin_site.register(PrizeCategory, PrizeCategoryAdmin)