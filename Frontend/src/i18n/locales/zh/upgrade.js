export default {
  title: "升級您的賣家帳號",
  subtitle: "商業帳號可刊登更多動物、上傳更多照片，並可舉辦拍賣。",
  subtitleNoAuctions: "商業帳號可刊登更多動物、上傳更多照片。",
  back: "返回帳號設定",
  loading: "正在載入方案…",
  loadError: "無法載入方案資訊。",
  current: "目前方案",
  choose: "選擇此方案",
  plans: {
    hobbyist: { name: "個人飼主", description: "適合偶爾轉讓或出售個體的飼主。" },
    commercial: { name: "商業賣家", description: "適合固定有個體供應的繁殖者與店家。" },
    commercial_paid: {
      name: "商業專業版",
      description: "適合大量出貨的賣家：最高刊登上限，拍賣手續費更低。",
      descriptionNoAuctions: "適合大量出貨的賣家：最高刊登上限。",
    },
  },
  launchOffer: "早期賣家優惠：{{date}}前發起的拍賣免收手續費。",
  price: {
    free: "免費",
    monthly: "每月 {{price}}",
  },
  features: {
    listings: "最多 {{count}} 則刊登",
    photos: "每則 {{count}} 張照片",
    auctions: "可舉辦拍賣",
    noAuctions: "無拍賣功能",
    auctionFeeFree: "拍賣成交目前免手續費（0%）",
    auctionFee: "拍賣成交手續費 {{percent}}",
  },
  checkout: {
    title: "改用{{plan}}",
    body: "目前尚未開放線上付款，方案由我們手動變更。請用帳號登記的電子郵件寫信給我們，並附上您的使用者名稱（{{username}}）。方案變更完成後，我們會回信通知您。",
    email: "寄信至 <email>{{email}}</email>",
    subject: "將 {{username}} 改為{{plan}}",
  },
};
