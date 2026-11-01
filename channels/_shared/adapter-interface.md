# Channel adapter interface
Agents talk to this interface, never to eBay or Shopify directly. Each channel implements:
list_products, publish_listing, update_price, update_stock, get_orders, mark_shipped, get_messages.
Adding a channel = a new folder in channels/ plus config.yml with enabled: true.
Single source of truth for products and stock is catalogue/.
