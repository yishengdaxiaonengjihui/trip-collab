/* 原型 mock 数据：西安 3 日游。所有内容为演示用假数据。 */

window.TRIP = {
  name: "西安 3 日游 · 国庆小分队",
  members: ["阿杰", "小雨", "老王", "小陈"],
  days: [
    { day: 1, date: "10月2日", label: "抵达 · 市区" },
    { day: 2, date: "10月3日", label: "东线 · 兵马俑" },
    { day: 3, date: "10月4日", label: "市区 · 返程" },
  ],
};

/* 初始定稿基线条目 */
window.BASE_ITEMS = [
  { id: "d1_arrive",    day: 1, time: "09:30", title: "抵达西安 · 高铁 G1001", note: "西安北站 → 大雁塔方向", refs: [],      amount: 515,  tag: "交通" },
  { id: "d1_pagoda",    day: 1, time: "14:00", title: "大雁塔",               note: "门票约 ¥50 · 傍晚有音乐喷泉", refs: [], amount: 100,  tag: "景点" },
  { id: "d1_night",     day: 1, time: "19:00", title: "大唐不夜城 · 晚餐",     note: "夜景步行街", refs: [],               amount: 300,  tag: "美食" },
  { id: "d1_hotel",     day: 1, time: "21:30", title: "全季酒店（大雁塔店）", note: "双床房 ×2 晚 · 含早", refs: [],      amount: 1200, tag: "住宿" },
  { id: "d2_terracotta", day: 2, time: "09:00", title: "兵马俑",              note: "需提前预约 · 游2路 / 地铁+打车", refs: ["d1_arrive"], amount: 240, tag: "景点" },
  { id: "d2_huaqing",   day: 2, time: "14:00", title: "华清宫",               note: "《长恨歌》演出可选", refs: [],        amount: 240,  tag: "景点" },
  { id: "d2_hui",       day: 2, time: "18:30", title: "回民街 · 晚餐",         note: "小吃自由发挥", refs: [],             amount: 200,  tag: "美食" },
  { id: "d3_museum",    day: 3, time: "09:00", title: "陕西历史博物馆",       note: "需提前 7 天预约！周一闭馆", refs: [], amount: 0,    tag: "景点" },
  { id: "d3_wall",      day: 3, time: "14:00", title: "城墙骑行",             note: "租车约 ¥45/人", refs: [],            amount: 90,   tag: "景点" },
  { id: "d3_train",     day: 3, time: "19:30", title: "返程 · 高铁 G2002",    note: "西安北站", refs: [],                 amount: 515,  tag: "交通" },
];

/* 种子提议：p_baomo 已采纳（当前定稿已含其修改）；p_morning、p_train 待审核 */
window.SEED_PROPOSALS = [
  {
    id: "p_baomo", author: "小雨", title: "D1 晚餐改吃羊肉泡馍",
    reason: "大唐不夜城人太多，泡馍更地道；老孙家总店离酒店近，吃完早点休息",
    status: "adopted", emergency: false, time: "10-01 20:15",
    events: [{ op: "update", id: "d1_night", changes: { title: "老孙家羊肉泡馍（总店）", time: "18:30" } }],
    comments: [{ who: "阿杰", text: "同意，泡馍排队快", time: "20:20" }],
  },
  {
    id: "p_morning", author: "老王", title: "D2 上午华清宫，下午兵马俑",
    reason: "避开兵马俑早高峰人流；华清宫上午光线好、人少",
    status: "pending", emergency: false, time: "10-01 21:02",
    events: [
      { op: "update", id: "d2_terracotta", changes: { time: "14:00", note: "下午场 · 避开早高峰" } },
      { op: "update", id: "d2_huaqing",    changes: { time: "09:00" } },
    ],
    comments: [],
  },
  {
    id: "p_train", author: "阿杰", title: "D1 改乘中午的高铁（睡懒觉）",
    reason: "想多睡会，改 G1003 中午到；大雁塔顺延到下午",
    status: "pending", emergency: false, time: "10-01 21:40",
    events: [
      { op: "update", id: "d1_arrive", changes: { time: "12:40", title: "抵达西安 · 高铁 G1003", note: "顺延：大雁塔改 14:30" } },
    ],
    comments: [{ who: "小雨", text: "那兵马俑的衔接时间也要看下？", time: "21:45" }],
  },
];
