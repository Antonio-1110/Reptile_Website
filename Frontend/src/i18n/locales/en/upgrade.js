export default {
  title: "Upgrade your seller account",
  subtitle: "Commercial accounts can list more animals, show more photos and run auctions.",
  subtitleNoAuctions: "Commercial accounts can list more animals and show more photos.",
  back: "Back to settings",
  loading: "Loading plans…",
  loadError: "Unable to load the available plans.",
  current: "Current plan",
  choose: "Choose this plan",
  plans: {
    hobbyist: { name: "Hobbyist", description: "For keepers rehoming or selling the occasional animal." },
    commercial: { name: "Commercial", description: "For breeders and shops with a regular stock of animals." },
    commercial_paid: {
      name: "Commercial Pro",
      description: "For high-volume sellers: the largest limits and a lower auction fee.",
      descriptionNoAuctions: "For high-volume sellers: the largest limits.",
    },
  },
  launchOffer: "Early seller offer: auctions you start before {{date}} have no fee.",
  price: {
    free: "Free",
    freeForNow: "Free for now",
  },
  features: {
    listings: "Up to {{count}} listings",
    photos: "{{count}} photos per listing",
    auctions: "Run auctions",
    noAuctions: "No auctions",
    auctionFeeFree: "0% fee on auction sales for now",
    auctionFee: "{{percent}} fee on auction sales",
  },
  checkout: {
    title: "Switching to {{plan}}",
    body: "Online payment isn't available yet, so we change plans by hand. Email us from the address on your account and include your username ({{username}}). We'll reply once your plan has changed.",
    email: "Email <email>{{email}}</email>",
    subject: "Switch {{username}} to {{plan}}",
  },
};
