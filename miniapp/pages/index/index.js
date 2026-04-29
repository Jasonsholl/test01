import { MANIFEST_URL } from "../../utils/config";

function joinUrl(base, relativePath) {
  const trimmedBase = base.replace(/\/+$/, "");
  const trimmedRel = relativePath.replace(/^\/+/, "");
  return `${trimmedBase}/${trimmedRel}`;
}

function deriveAssetBase(manifestUrl) {
  // manifestUrl should end with `/site/manifest.json`
  const idx = manifestUrl.indexOf("/site/manifest.json");
  if (idx === -1) return manifestUrl;
  return manifestUrl.slice(0, idx + "/site".length);
}

Page({
  data: {
    loading: false,
    updatedAt: "",
    count: 0,
    items: []
  },

  onLoad() {
    this.refresh();
  },

  onPullDownRefresh() {
    this.refresh().finally(() => wx.stopPullDownRefresh());
  },

  refresh() {
    this.setData({ loading: true });
    const url = `${MANIFEST_URL}?ts=${Date.now()}`;
    return new Promise((resolve, reject) => {
      wx.request({
        url,
        method: "GET",
        success: (res) => {
          const data = res.data || {};
          const assetBase = deriveAssetBase(MANIFEST_URL);
          const items = (data.items || []).map((it) => ({
            ...it,
            url: joinUrl(assetBase, it.path)
          }));
          this.setData({
            updatedAt: data.updatedAt || "",
            count: data.count || items.length,
            items
          });
          resolve();
        },
        fail: (err) => reject(err),
        complete: () => this.setData({ loading: false })
      });
    });
  },

  onPreview(e) {
    const idx = Number(e.currentTarget.dataset.index || 0);
    const urls = this.data.items.map((it) => it.url);
    const current = urls[idx] || urls[0];
    if (!current) return;
    wx.previewImage({ current, urls });
  }
});

