# Product images

Drop an image file here named after a product's **SKU** for a photo unique to
that product:

```
sku-1001.png   # Ceramic Pour-Over Dripper
sku-1002.jpg   # Braided Leather Bookmark
sku-1003.webp  # Wireless Earbud Case Skin
...
```

(SKU matching is case-insensitive — `SKU-1001.png` and `sku-1001.png` both work.)

You can also name a file after a **category** (`home.png`, `gifts.jpg`,
`electronics.webp`, `stationery.png`, `toys.png`) to use it as a shared
placeholder for every product in that category that doesn't have its own
SKU image, and a `fallback.png` for anything else.

Lookup order per product: SKU image → category image → `fallback.png` →
emoji/gradient placeholder.

Supported extensions: `.png`, `.jpg`, `.jpeg`, `.webp`, `.svg`.

`ProductGrid.vue` picks these up automatically by filename — no code changes
needed, just drop the file and Vite hot-reloads.
