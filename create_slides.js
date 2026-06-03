const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "DS200 Team";
pres.title = "DS200 Big Data";

// ======= THEME =======
const BG = "0B1D3A";
const BG2 = "132E4F";
const WHITE = "FFFFFF";
const CYAN = "00D4FF";
const BLUE2 = "4A90D9";
const GOLD = "FFD700";
const TBL_HDR = "1B4F72";
const TBL_ROW1 = "0E2A47";
const TBL_ROW2 = "162D50";
const MUTED = "A8D8EA";
const CARD_BG = "0F2740";
const CARD_BORDER = "1A5276";

function bg(slide) { slide.background = { color: BG }; }

function title(slide, text) {
  slide.addText(text, { x: 0.5, y: 0.25, w: 9, h: 0.65, fontSize: 26, fontFace: "Calibri", color: WHITE, bold: true, margin: 0 });
  slide.addShape(pres.shapes.LINE, { x: 0.5, y: 0.92, w: 2.5, h: 0, line: { color: CYAN, width: 2.5 } });
}

function tableRows(headers, data) {
  const hdr = headers.map(h => ({ text: h, options: { bold: true, color: WHITE, fontSize: 13, fontFace: "Calibri", fill: { color: TBL_HDR }, align: "left", valign: "middle" } }));
  const rows = data.map((row, i) =>
    row.map(cell => {
      const isObj = typeof cell === "object" && cell !== null && cell.text;
      const txt = isObj ? cell.text : String(cell);
      const opts = { color: WHITE, fontSize: 12, fontFace: "Calibri", fill: { color: i % 2 === 0 ? TBL_ROW1 : TBL_ROW2 }, align: "left", valign: "middle" };
      if (isObj && cell.bold) opts.bold = true;
      return { text: txt, options: opts };
    })
  );
  return [hdr, ...rows];
}

function card(slide, x, y, w, h) {
  slide.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: CARD_BG }, line: { color: CARD_BORDER, width: 1 } });
}

function toolBox(slide, text, y) {
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y, w: 9, h: 0.45, fill: { color: "0A2540" }, line: { color: CYAN, width: 1.2 } });
  slide.addText(text, { x: 0.7, y, w: 8.6, h: 0.45, fontSize: 13, fontFace: "Calibri", color: CYAN, bold: true, valign: "middle", margin: 0 });
}

// ======= SLIDE 1 — TITLE =======
let s1 = pres.addSlide(); bg(s1);
s1.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 5.625, fill: { color: "081529" } });
s1.addShape(pres.shapes.LINE, { x: 2, y: 1.1, w: 6, h: 0, line: { color: CYAN, width: 1 } });
s1.addText("HỆ THỐNG THU THẬP DỮ LIỆU ĐIỆN THOẠI\nĐA PHƯƠNG THỨC VÀ PHÂN TÍCH\nTRẢI NGHIỆM NGƯỜI DÙNG", { x: 0.5, y: 1.2, w: 9, h: 1.8, fontSize: 26, fontFace: "Calibri", color: WHITE, bold: true, align: "center", valign: "middle", lineSpacingMultiple: 1.2 });
s1.addShape(pres.shapes.LINE, { x: 2, y: 3.1, w: 6, h: 0, line: { color: CYAN, width: 1 } });
s1.addText("Đồ án DS200 — Big Data", { x: 0.5, y: 3.2, w: 9, h: 0.4, fontSize: 18, fontFace: "Calibri", color: CYAN, align: "center", italic: true });
s1.addText([
  { text: "Thành viên:  ", options: { color: MUTED, fontSize: 13, bold: true } },
  { text: "[Tên SV 1] — [MSSV]   |   [Tên SV 2] — [MSSV]", options: { color: WHITE, fontSize: 13 } }
], { x: 0.5, y: 3.85, w: 9, h: 0.35, fontFace: "Calibri", align: "center" });
s1.addText([
  { text: "GVHD:  ", options: { color: MUTED, fontSize: 13, bold: true } },
  { text: "[Tên Giảng viên]", options: { color: WHITE, fontSize: 13 } }
], { x: 0.5, y: 4.2, w: 9, h: 0.35, fontFace: "Calibri", align: "center" });
s1.addText("Tháng 6/2026", { x: 0.5, y: 4.8, w: 9, h: 0.3, fontSize: 12, fontFace: "Calibri", color: MUTED, align: "center" });

// ======= SLIDE 2 — MỤC LỤC =======
let s2 = pres.addSlide(); bg(s2);
title(s2, "NỘI DUNG TRÌNH BÀY");
const tocItems = [
  "Tổng quan bộ dữ liệu & Thống kê",
  "Thu thập dữ liệu (Crawling)",
  "Xử lý & Làm sạch dữ liệu",
  "Thiết kế cơ sở dữ liệu (Star Schema)",
  "Thu thập YouTube Media & Lưu trữ S3",
  "Phân loại bình luận & Embedding",
  "Hệ thống RAG — Agentic AI",
  "Tổng kết & Hướng phát triển"
];
tocItems.forEach((item, i) => {
  const yPos = 1.25 + i * 0.48;
  s2.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: yPos, w: 0.45, h: 0.38, fill: { color: i < 6 ? BLUE2 : (i === 6 ? "1B7A4A" : GOLD) } });
  s2.addText(String(i + 1), { x: 0.5, y: yPos, w: 0.45, h: 0.38, fontSize: 15, fontFace: "Calibri", color: WHITE, bold: true, align: "center", valign: "middle", margin: 0 });
  s2.addText(item, { x: 1.15, y: yPos, w: 8, h: 0.38, fontSize: 16, fontFace: "Calibri", color: WHITE, valign: "middle", margin: 0 });
});

// ======= SLIDE 3 — TỔNG QUAN =======
let s3 = pres.addSlide(); bg(s3);
title(s3, "TỔNG QUAN BỘ DỮ LIỆU");
const stats = [
  { num: "~1,500+", label: "Sản phẩm\nsmartphone" },
  { num: "12,800+", label: "Bình luận\nYouTube" },
  { num: "12", label: "Bảng dữ liệu\n(Star Schema)" },
  { num: "768D", label: "Vector\nEmbeddings" }
];
stats.forEach((st, i) => {
  const xPos = 0.5 + i * 2.35;
  card(s3, xPos, 1.4, 2.1, 2.2);
  s3.addText(st.num, { x: xPos, y: 1.6, w: 2.1, h: 0.8, fontSize: 36, fontFace: "Calibri", color: GOLD, bold: true, align: "center", valign: "middle", margin: 0 });
  s3.addText(st.label, { x: xPos, y: 2.5, w: 2.1, h: 0.8, fontSize: 14, fontFace: "Calibri", color: MUTED, align: "center", valign: "top", margin: 0 });
});
s3.addText("Nguồn: MobileCity  +  YouTube Data API  +  YouTube Comments", { x: 0.5, y: 4.2, w: 9, h: 0.4, fontSize: 13, fontFace: "Calibri", color: MUTED, align: "center" });

// ======= SLIDE 4 — PHÂN BỐ DIMENSION =======
let s4 = pres.addSlide(); bg(s4);
title(s4, "PHÂN BỐ DỮ LIỆU THEO DIMENSION");
s4.addTable(tableRows(["Dimension", "Số trường", "Mô tả"], [
  ["dim_display", "6", "Màn hình, độ phân giải, cảm ứng"],
  ["dim_camera", "6", "Camera trước/sau, flash, quay video"],
  ["dim_performance", "5", "Chipset, CPU, GPU, RAM"],
  ["dim_storage", "4", "Bộ nhớ trong/ngoài"],
  ["dim_design", "3", "Kiểu dáng, kích thước, trọng lượng"],
  ["dim_battery", "3", "Loại pin, dung lượng"],
  ["dim_connectivity", "13", "WiFi, Bluetooth, NFC, SIM, GPS..."],
  ["dim_utilities", "6", "Phát media, radio, tính năng khác"],
]), { x: 0.5, y: 1.15, w: 9, colW: [2.5, 1.5, 5], border: { pt: 0.5, color: "2C3E50" }, rowH: [0.42, 0.42, 0.42, 0.42, 0.42, 0.42, 0.42, 0.42, 0.42] });

// ======= SLIDE 5 — FACT TABLE =======
let s5 = pres.addSlide(); bg(s5);
title(s5, "BẢNG FACT_PRODUCT — HUB TRUNG TÂM");
s5.addTable(tableRows(["Cột", "Kiểu", "Vai trò"], [
  ["product_id", "INTEGER PK", "Khóa chính, auto-increment"],
  ["product_name", "VARCHAR(255)", "Tên sản phẩm (chuẩn hóa LLM)"],
  ["os_version", "TEXT", "Phiên bản hệ điều hành"],
  ["price", "INTEGER", "Giá VNĐ"],
  ["picture_url", "VARCHAR", "URL hình sản phẩm"],
  ["created_at", "TIMESTAMP", "Thời gian tạo"],
]), { x: 0.5, y: 1.15, w: 9, colW: [2.5, 2.5, 4], border: { pt: 0.5, color: "2C3E50" }, rowH: [0.45, 0.45, 0.45, 0.45, 0.45, 0.45, 0.45] });
s5.addText("Liên kết 1-N tới 8 bảng Dimension qua product_id (Foreign Key)", { x: 0.5, y: 4.6, w: 9, h: 0.4, fontSize: 13, fontFace: "Calibri", color: GOLD, italic: true, align: "center" });

// ======= SLIDE 6 — YOUTUBE & S3 =======
let s6 = pres.addSlide(); bg(s6);
title(s6, "DỮ LIỆU YOUTUBE & LƯU TRỮ S3");
// Left cards
const s6cards = [
  { num: "3 loại media", desc: "Audio MP3 · Comments CSV · Transcripts JSON" },
  { num: "AWS S3", desc: "Bucket: smartphone-data-s3 (ap-southeast-1)" },
  { num: "2 bảng RDS", desc: "dim_video_transcripts + dim_video_comments" },
];
s6cards.forEach((c, i) => {
  const yy = 1.2 + i * 1.2;
  card(s6, 0.5, yy, 4.3, 1.0);
  s6.addText(c.num, { x: 0.7, y: yy + 0.05, w: 3.9, h: 0.4, fontSize: 16, fontFace: "Calibri", color: GOLD, bold: true, margin: 0 });
  s6.addText(c.desc, { x: 0.7, y: yy + 0.5, w: 3.9, h: 0.4, fontSize: 12, fontFace: "Calibri", color: MUTED, margin: 0 });
});
// Right: S3 tree
card(s6, 5.1, 1.2, 4.4, 3.5);
s6.addText("Cấu trúc S3 Bucket", { x: 5.3, y: 1.3, w: 4, h: 0.35, fontSize: 14, fontFace: "Calibri", color: CYAN, bold: true, margin: 0 });
s6.addText([
  { text: "s3://smartphone-data-s3/\n", options: { color: GOLD, fontSize: 12, bold: true, breakLine: true } },
  { text: "  audio/{product}/{id}_audio.mp3\n", options: { color: WHITE, fontSize: 11, breakLine: true } },
  { text: "  comments/{product}/{id}_comments.csv\n", options: { color: WHITE, fontSize: 11, breakLine: true } },
  { text: "  transcripts/{product}/{id}_transcript.json\n", options: { color: WHITE, fontSize: 11, breakLine: true } },
  { text: "  media_log/{date}/{product}.log", options: { color: MUTED, fontSize: 11 } },
], { x: 5.3, y: 1.75, w: 4, h: 2.5, fontFace: "Consolas", valign: "top", margin: 0 });

// ======= SLIDE 7 — PIPELINE =======
let s7 = pres.addSlide(); bg(s7);
title(s7, "PIPELINE XỬ LÝ DỮ LIỆU — 10 BƯỚC");
const steps = [
  ["1", "Crawl\nLinks"], ["2", "Crawl\nSpecs"], ["3", "Dedup\nMD5"], ["4", "LLM\nNormalize"], ["5", "Final\nDedup"],
  ["6", "Bootstrap\nDB"], ["7", "Load\nRDS"], ["8", "YouTube\nMedia"], ["9", "Classify\nComments"], ["10", "Embedding"]
];
// Row 1: steps 1-5
steps.slice(0, 5).forEach((st, i) => {
  const xp = 0.35 + i * 1.92;
  s7.addShape(pres.shapes.RECTANGLE, { x: xp, y: 1.4, w: 1.65, h: 1.3, fill: { color: CARD_BG }, line: { color: BLUE2, width: 1.2 } });
  s7.addText(st[0], { x: xp, y: 1.4, w: 0.4, h: 0.35, fontSize: 12, fontFace: "Calibri", color: BG, bold: true, fill: { color: CYAN }, align: "center", valign: "middle", margin: 0 });
  s7.addText(st[1], { x: xp, y: 1.8, w: 1.65, h: 0.8, fontSize: 12, fontFace: "Calibri", color: WHITE, align: "center", valign: "middle", margin: 0 });
  if (i < 4) s7.addText("→", { x: xp + 1.65, y: 1.7, w: 0.27, h: 0.5, fontSize: 20, fontFace: "Calibri", color: CYAN, align: "center", valign: "middle", margin: 0 });
});
// Row 2: steps 6-10
steps.slice(5).forEach((st, i) => {
  const xp = 0.35 + i * 1.92;
  s7.addShape(pres.shapes.RECTANGLE, { x: xp, y: 3.2, w: 1.65, h: 1.3, fill: { color: CARD_BG }, line: { color: "1B7A4A", width: 1.2 } });
  s7.addText(st[0], { x: xp, y: 3.2, w: 0.4, h: 0.35, fontSize: 12, fontFace: "Calibri", color: BG, bold: true, fill: { color: GOLD }, align: "center", valign: "middle", margin: 0 });
  s7.addText(st[1], { x: xp, y: 3.6, w: 1.65, h: 0.8, fontSize: 12, fontFace: "Calibri", color: WHITE, align: "center", valign: "middle", margin: 0 });
  if (i < 4) s7.addText("→", { x: xp + 1.65, y: 3.5, w: 0.27, h: 0.5, fontSize: 20, fontFace: "Calibri", color: GOLD, align: "center", valign: "middle", margin: 0 });
});

// ======= SLIDE 8 — CRAWL LINKS =======
let s8 = pres.addSlide(); bg(s8);
title(s8, "GIAI ĐOẠN 1A: CÀO DANH SÁCH SẢN PHẨM");
toolBox(s8, "Công cụ:  requests  +  BeautifulSoup  |  Nguồn: MobileCity", 1.15);
s8.addText([
  { text: "Cào tất cả category slugs & trang danh sách sản phẩm", options: { bullet: true, breakLine: true, color: WHITE, fontSize: 15 } },
  { text: "Throttle: sleep(0.8s), retry mechanism, pagination tự động", options: { bullet: true, breakLine: true, color: WHITE, fontSize: 15 } },
  { text: "Checkpoint để tránh mất dữ liệu khi gián đoạn", options: { bullet: true, color: WHITE, fontSize: 15 } },
], { x: 0.5, y: 1.85, w: 9, h: 1.5, fontFace: "Calibri", paraSpaceAfter: 8 });
card(s8, 0.5, 3.5, 9, 1.5);
s8.addText("Đầu ra: product_links.json", { x: 0.7, y: 3.55, w: 8, h: 0.35, fontSize: 14, fontFace: "Calibri", color: GOLD, bold: true, margin: 0 });
s8.addText("Chứa: product_name, url, price_vnd, image, slug", { x: 0.7, y: 3.95, w: 8, h: 0.3, fontSize: 13, fontFace: "Calibri", color: MUTED, margin: 0 });
s8.addText("Config: max_pages_per_slug = 60", { x: 0.7, y: 4.35, w: 8, h: 0.3, fontSize: 13, fontFace: "Calibri", color: MUTED, margin: 0 });

// ======= SLIDE 9 — CRAWL SPECS =======
let s9 = pres.addSlide(); bg(s9);
title(s9, "GIAI ĐOẠN 1B: CÀO THÔNG SỐ KỸ THUẬT");
toolBox(s9, "Công cụ:  BeautifulSoup  —  Parse bảng specs HTML", 1.15);
s9.addText([
  { text: "Truy cập từng URL sản phẩm, parse bảng thông số kỹ thuật", options: { bullet: true, breakLine: true, color: WHITE, fontSize: 15 } },
  { text: "Tự động ánh xạ tên trường tiếng Việt sang schema DB", options: { bullet: true, breakLine: true, color: WHITE, fontSize: 15 } },
  { text: "Checkpoint mỗi 50 bản ghi — chống mất dữ liệu", options: { bullet: true, color: WHITE, fontSize: 15 } },
], { x: 0.5, y: 1.85, w: 9, h: 1.3, fontFace: "Calibri", paraSpaceAfter: 8 });
card(s9, 0.5, 3.35, 9, 1.7);
s9.addText("Đầu ra: all_product_specs_raw.json", { x: 0.7, y: 3.4, w: 8, h: 0.35, fontSize: 14, fontFace: "Calibri", color: GOLD, bold: true, margin: 0 });
s9.addText("9 nhóm trường: fact_product + 8 dimensions (display, camera, performance, storage, design, battery, connectivity, utilities)", { x: 0.7, y: 3.85, w: 8.4, h: 0.6, fontSize: 13, fontFace: "Calibri", color: MUTED, margin: 0 });

// ======= SLIDE 10 — DEDUP MD5 =======
let s10 = pres.addSlide(); bg(s10);
title(s10, "GIAI ĐOẠN 2A: KHỬ TRÙNG LẶP (MD5 HASH)");
toolBox(s10, "Phương pháp:  MD5 Hash trên 7 thuộc tính phần cứng bất biến", 1.15);
s10.addTable(tableRows(["#", "Trường", "Bảng nguồn"], [
  ["1", "chipset", "dim_performance"],
  ["2", "core_count", "dim_performance"],
  ["3", "ram_capacity", "dim_performance"],
  ["4", "gpu_chip", "dim_performance"],
  ["5", "dimensions", "dim_design"],
  ["6", "weight", "dim_design"],
  ["7", "battery_capacity", "dim_battery"],
]), { x: 0.5, y: 1.8, w: 6, colW: [0.6, 2.4, 3], border: { pt: 0.5, color: "2C3E50" }, rowH: [0.35, 0.35, 0.35, 0.35, 0.35, 0.35, 0.35, 0.35] });
card(s10, 6.8, 1.8, 2.7, 2.8);
s10.addText("Key Insight", { x: 6.95, y: 1.9, w: 2.4, h: 0.35, fontSize: 13, fontFace: "Calibri", color: CYAN, bold: true, margin: 0 });
s10.addText("Phần cứng\n= bất biến", { x: 6.95, y: 2.35, w: 2.4, h: 0.8, fontSize: 20, fontFace: "Calibri", color: GOLD, bold: true, align: "center", margin: 0 });
s10.addText("Tên marketing\n= thay đổi", { x: 6.95, y: 3.3, w: 2.4, h: 0.8, fontSize: 16, fontFace: "Calibri", color: MUTED, align: "center", margin: 0 });

// ======= SLIDE 11 — LLM NORMALIZE =======
let s11 = pres.addSlide(); bg(s11);
title(s11, "GIAI ĐOẠN 2B: CHUẨN HÓA TÊN BẰNG LLM");
toolBox(s11, "Model:  OpenAI GPT  ·  temperature = 0.1  (deterministic)", 1.15);
// Flow diagram
s11.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.9, w: 2.8, h: 0.7, fill: { color: TBL_ROW1 }, line: { color: BLUE2, width: 1 } });
s11.addText("product_name\nchipset + storage", { x: 0.5, y: 1.9, w: 2.8, h: 0.7, fontSize: 12, fontFace: "Calibri", color: WHITE, align: "center", valign: "middle", margin: 0 });
s11.addText("→", { x: 3.35, y: 1.9, w: 0.5, h: 0.7, fontSize: 28, fontFace: "Calibri", color: CYAN, align: "center", valign: "middle", margin: 0 });
s11.addShape(pres.shapes.RECTANGLE, { x: 3.9, y: 1.9, w: 2.0, h: 0.7, fill: { color: "1B7A4A" }, line: { color: GOLD, width: 1.2 } });
s11.addText("GPT", { x: 3.9, y: 1.9, w: 2.0, h: 0.7, fontSize: 18, fontFace: "Calibri", color: WHITE, bold: true, align: "center", valign: "middle", margin: 0 });
s11.addText("→", { x: 5.95, y: 1.9, w: 0.5, h: 0.7, fontSize: 28, fontFace: "Calibri", color: CYAN, align: "center", valign: "middle", margin: 0 });
s11.addShape(pres.shapes.RECTANGLE, { x: 6.5, y: 1.9, w: 3, h: 0.7, fill: { color: TBL_ROW1 }, line: { color: BLUE2, width: 1 } });
s11.addText("search_query_name", { x: 6.5, y: 1.9, w: 3, h: 0.7, fontSize: 13, fontFace: "Calibri", color: GOLD, bold: true, align: "center", valign: "middle", margin: 0 });
// Example
card(s11, 0.5, 2.9, 9, 1.8);
s11.addText("Ví dụ:", { x: 0.7, y: 2.95, w: 2, h: 0.35, fontSize: 13, fontFace: "Calibri", color: CYAN, bold: true, margin: 0 });
s11.addText("Before:", { x: 0.7, y: 3.3, w: 1, h: 0.3, fontSize: 12, fontFace: "Calibri", color: MUTED, bold: true, margin: 0 });
s11.addText("\"Điện thoại Samsung Galaxy S24 Ultra 5G 256GB Chính hãng Mới 100%\"", { x: 1.7, y: 3.3, w: 7.5, h: 0.35, fontSize: 12, fontFace: "Calibri", color: WHITE, margin: 0 });
s11.addText("After:", { x: 0.7, y: 3.7, w: 1, h: 0.3, fontSize: 12, fontFace: "Calibri", color: MUTED, bold: true, margin: 0 });
s11.addText("\"Samsung Galaxy S24 Ultra Snapdragon 8 Gen 3\"", { x: 1.7, y: 3.7, w: 7.5, h: 0.35, fontSize: 12, fontFace: "Calibri", color: GOLD, margin: 0 });
s11.addText("Rate limiting: auto-save mỗi 100 mẫu  ·  sleep 30s giữa batch", { x: 0.7, y: 4.15, w: 8.5, h: 0.3, fontSize: 11, fontFace: "Calibri", color: MUTED, italic: true, margin: 0 });

// ======= SLIDE 12 — FINAL DEDUP + LOAD =======
let s12 = pres.addSlide(); bg(s12);
title(s12, "GIAI ĐOẠN 2C: KHỬ TRÙNG CUỐI & NẠP VÀO RDS");
toolBox(s12, "Công cụ:  SQLAlchemy ORM  ·  PostgreSQL (AWS RDS)", 1.15);
// Two columns
card(s12, 0.5, 1.85, 4.15, 2.0);
s12.addText("Final Deduplication", { x: 0.7, y: 1.9, w: 3.7, h: 0.35, fontSize: 15, fontFace: "Calibri", color: CYAN, bold: true, margin: 0 });
s12.addText([
  { text: "Loại bỏ search_query_name trùng nhau", options: { bullet: true, breakLine: true, color: WHITE, fontSize: 13 } },
  { text: "Giữ lần xuất hiện đầu tiên", options: { bullet: true, breakLine: true, color: WHITE, fontSize: 13 } },
  { text: "Đầu ra: final_ready_to_load_specs.json", options: { bullet: true, color: GOLD, fontSize: 13 } },
], { x: 0.7, y: 2.3, w: 3.7, h: 1.3, fontFace: "Calibri", paraSpaceAfter: 6 });

card(s12, 5.05, 1.85, 4.45, 2.0);
s12.addText("Load to RDS", { x: 5.25, y: 1.9, w: 4, h: 0.35, fontSize: 15, fontFace: "Calibri", color: CYAN, bold: true, margin: 0 });
s12.addText([
  { text: "INSERT fact_product (lấy product_id)", options: { bullet: true, breakLine: true, color: WHITE, fontSize: 13 } },
  { text: "INSERT 8 dim_* tables (FK → product_id)", options: { bullet: true, breakLine: true, color: WHITE, fontSize: 13 } },
  { text: "ACID transactions đảm bảo toàn vẹn", options: { bullet: true, color: GOLD, fontSize: 13 } },
], { x: 5.25, y: 2.3, w: 4, h: 1.3, fontFace: "Calibri", paraSpaceAfter: 6 });
s12.addText("Chế độ: --truncate (xóa sạch & nạp lại)  |  --append (chỉ thêm mới)", { x: 0.5, y: 4.2, w: 9, h: 0.4, fontSize: 13, fontFace: "Calibri", color: MUTED, align: "center" });

// ======= SLIDE 13 — STAR SCHEMA =======
let s13 = pres.addSlide(); bg(s13);
title(s13, "THIẾT KẾ CƠ SỞ DỮ LIỆU — STAR SCHEMA");
// Center fact
s13.addShape(pres.shapes.OVAL, { x: 3.65, y: 2.0, w: 2.7, h: 1.5, fill: { color: "B8860B" }, line: { color: GOLD, width: 2 } });
s13.addText("fact_product", { x: 3.65, y: 2.0, w: 2.7, h: 1.5, fontSize: 15, fontFace: "Calibri", color: WHITE, bold: true, align: "center", valign: "middle", margin: 0 });
// 8 dimensions around
const dims = [
  { name: "dim_display", x: 0.3, y: 0.3 }, { name: "dim_camera", x: 3.65, y: 0.2 },
  { name: "dim_performance", x: 7.0, y: 0.3 }, { name: "dim_storage", x: 8.0, y: 2.1 },
  { name: "dim_design", x: 7.0, y: 3.8 }, { name: "dim_battery", x: 3.65, y: 4.2 },
  { name: "dim_connectivity", x: 0.3, y: 3.8 }, { name: "dim_utilities", x: -0.4, y: 2.1 },
];
dims.forEach(d => {
  s13.addShape(pres.shapes.RECTANGLE, { x: d.x, y: d.y, w: 2.35, h: 0.7, fill: { color: TBL_HDR }, line: { color: BLUE2, width: 1 } });
  s13.addText(d.name, { x: d.x, y: d.y, w: 2.35, h: 0.7, fontSize: 11, fontFace: "Calibri", color: WHITE, bold: true, align: "center", valign: "middle", margin: 0 });
});
s13.addText("Mỗi dimension kết nối qua product_id (Foreign Key)", { x: 0.5, y: 5.05, w: 9, h: 0.3, fontSize: 12, fontFace: "Calibri", color: MUTED, align: "center" });

// ======= SLIDE 14 — DIM DETAIL 1/2 =======
let s14 = pres.addSlide(); bg(s14);
title(s14, "CHI TIẾT CÁC BẢNG DIMENSION (1/2)");
s14.addTable(tableRows(["Bảng", "Các trường chính"], [
  [{ text: "dim_display", bold: true }, "display_type, resolution, screen_size, touch_technology, color_depth, display_standard"],
  [{ text: "dim_camera", bold: true }, "rear_camera, front_camera, flash_light, camera_features, video_recording, video_call"],
  [{ text: "dim_performance", bold: true }, "chipset, cpu_speed, core_count, ram_capacity, gpu_chip"],
  [{ text: "dim_storage", bold: true }, "internal_storage, external_memory, max_external_support, phonebook_storage"],
]), { x: 0.5, y: 1.15, w: 9, colW: [2.5, 6.5], border: { pt: 0.5, color: "2C3E50" }, rowH: [0.45, 0.65, 0.65, 0.55, 0.55] });

// ======= SLIDE 15 — DIM DETAIL 2/2 =======
let s15 = pres.addSlide(); bg(s15);
title(s15, "CHI TIẾT CÁC BẢNG DIMENSION (2/2)");
s15.addTable(tableRows(["Bảng", "Các trường chính"], [
  [{ text: "dim_design", bold: true }, "design_style, dimensions, weight"],
  [{ text: "dim_battery", bold: true }, "battery_type, battery_capacity, removable_battery"],
  [{ text: "dim_connectivity", bold: true }, "wifi, bluetooth, nfc, sim_type, sim_slots, gps, network_3g/4g, usb, charging_port..."],
  [{ text: "dim_utilities", bold: true }, "movie_playback, music_playback, voice_recorder, fm_radio, other_features"],
]), { x: 0.5, y: 1.15, w: 9, colW: [2.5, 6.5], border: { pt: 0.5, color: "2C3E50" }, rowH: [0.45, 0.5, 0.5, 0.6, 0.5] });
s15.addText("Tất cả dim tables đều có thêm: youtuber_review (JSON), user_review (JSON), last_updated", { x: 0.5, y: 4.0, w: 9, h: 0.4, fontSize: 13, fontFace: "Calibri", color: GOLD, italic: true, align: "center" });

// ======= SLIDE 16 — YOUTUBE MEDIA =======
let s16 = pres.addSlide(); bg(s16);
title(s16, "THU THẬP DỮ LIỆU YOUTUBE");
toolBox(s16, "Công cụ:  YouTube Data API  ·  yt-dlp  ·  youtube-transcript-api", 1.15);
s16.addText([
  { text: "Search YouTube API: query \"review {product_name}\", regionCode=\"VN\"", options: { bullet: true, breakLine: true, color: WHITE, fontSize: 14 } },
  { text: "API Key Pool (thread-safe): auto-rotate khi hết quota (HTTP 403)", options: { bullet: true, breakLine: true, color: WHITE, fontSize: 14 } },
  { text: "ThreadPoolExecutor: 3 workers song song, mỗi product 1 thread", options: { bullet: true, color: WHITE, fontSize: 14 } },
], { x: 0.5, y: 1.85, w: 9, h: 1.2, fontFace: "Calibri", paraSpaceAfter: 6 });
// 3 media types table
s16.addTable(tableRows(["Loại", "Công cụ", "Output"], [
  ["Audio", "yt-dlp (-x --audio-format mp3)", ".mp3"],
  ["Comments", "yt-dlp (--write-comments)", ".csv"],
  ["Transcript", "youtube-transcript-api (vi > en)", ".json"],
]), { x: 0.5, y: 3.25, w: 9, colW: [2, 5, 2], border: { pt: 0.5, color: "2C3E50" }, rowH: [0.42, 0.42, 0.42, 0.42] });

// ======= SLIDE 17 — S3 UPLOAD =======
let s17 = pres.addSlide(); bg(s17);
title(s17, "LƯU TRỮ AWS S3 & METADATA");
toolBox(s17, "Công cụ:  boto3 (AWS SDK)  ·  S3 Bucket: smartphone-data-s3", 1.15);
// Flow steps
const s17steps = [
  { n: "1", t: "Tải về\nlocal tạm" }, { n: "2", t: "Upload\nS3" }, { n: "3", t: "Xóa file\ntạm" }, { n: "4", t: "Lưu S3 path\nvào RDS" }
];
s17steps.forEach((st, i) => {
  const xp = 0.5 + i * 2.35;
  s17.addShape(pres.shapes.RECTANGLE, { x: xp, y: 1.9, w: 2.05, h: 1.0, fill: { color: CARD_BG }, line: { color: BLUE2, width: 1 } });
  s17.addText(st.n, { x: xp, y: 1.9, w: 0.35, h: 0.3, fontSize: 11, fontFace: "Calibri", color: BG, bold: true, fill: { color: CYAN }, align: "center", valign: "middle", margin: 0 });
  s17.addText(st.t, { x: xp, y: 2.2, w: 2.05, h: 0.6, fontSize: 13, fontFace: "Calibri", color: WHITE, align: "center", valign: "middle", margin: 0 });
  if (i < 3) s17.addText("→", { x: xp + 2.05, y: 2.05, w: 0.3, h: 0.7, fontSize: 22, fontFace: "Calibri", color: CYAN, align: "center", valign: "middle", margin: 0 });
});
// Metadata tables
card(s17, 0.5, 3.3, 9, 1.8);
s17.addText("Metadata lưu vào RDS:", { x: 0.7, y: 3.35, w: 8, h: 0.35, fontSize: 14, fontFace: "Calibri", color: CYAN, bold: true, margin: 0 });
s17.addText([
  { text: "dim_video_transcripts: ", options: { bold: true, color: GOLD, fontSize: 13 } },
  { text: "video_id, product_id, youtube_url, s3_audio_path, s3_transcript_path, s3_comments_path", options: { color: WHITE, fontSize: 12 } },
], { x: 0.7, y: 3.75, w: 8.5, h: 0.4, fontFace: "Calibri", margin: 0 });
s17.addText([
  { text: "dim_video_comments: ", options: { bold: true, color: GOLD, fontSize: 13 } },
  { text: "comment_id, video_id (FK), user_name, comment_text, created_at", options: { color: WHITE, fontSize: 12 } },
], { x: 0.7, y: 4.2, w: 8.5, h: 0.4, fontFace: "Calibri", margin: 0 });

// ======= SLIDE 18 — COMMENT CLASSIFICATION =======
let s18 = pres.addSlide(); bg(s18);
title(s18, "PHÂN LOẠI BÌNH LUẬN THEO KHÍA CẠNH");
toolBox(s18, "Phương pháp:  Regex Keyword Matching (word boundary \\b)  ·  _aspect_keywords.py", 1.15);
// Vocab table (left)
s18.addTable(tableRows(["Aspect", "Ví dụ keywords"], [
  ["display", "màn hình, oled, screen, 120Hz"],
  ["camera", "chụp, zoom, selfie, 48MP"],
  ["battery", "pin, sạc nhanh, 5000mAh"],
  ["performance", "lag, mượt, game, snapdragon"],
  ["design", "thiết kế, mỏng, nhẹ, premium"],
  ["storage", "bộ nhớ, rom, 256GB"],
  ["connectivity", "wifi, 5g, bluetooth, nfc"],
  ["utilities", "vân tay, chống nước, ip68"],
]), { x: 0.5, y: 1.8, w: 5.5, colW: [1.8, 3.7], border: { pt: 0.5, color: "2C3E50" }, rowH: [0.35, 0.35, 0.35, 0.35, 0.35, 0.35, 0.35, 0.35, 0.35] });
// Example (right)
card(s18, 6.3, 1.8, 3.2, 3.15);
s18.addText("Ví dụ kết quả", { x: 6.5, y: 1.85, w: 2.8, h: 0.35, fontSize: 13, fontFace: "Calibri", color: CYAN, bold: true, margin: 0 });
s18.addText("\"Camera đẹp, pin trâu\"", { x: 6.5, y: 2.3, w: 2.8, h: 0.35, fontSize: 12, fontFace: "Calibri", color: WHITE, italic: true, margin: 0 });
s18.addText("↓", { x: 6.5, y: 2.65, w: 2.8, h: 0.3, fontSize: 18, fontFace: "Calibri", color: CYAN, align: "center", margin: 0 });
s18.addText("{\"camera\": 1,\n \"battery\": 1}", { x: 6.5, y: 2.95, w: 2.8, h: 0.6, fontSize: 12, fontFace: "Consolas", color: GOLD, margin: 0 });
s18.addText("1 comment có thể\nthuộc nhiều aspect", { x: 6.5, y: 3.7, w: 2.8, h: 0.5, fontSize: 11, fontFace: "Calibri", color: MUTED, italic: true, margin: 0 });

// ======= SLIDE 19 — AGGREGATION =======
let s19 = pres.addSlide(); bg(s19);
title(s19, "GOM BÌNH LUẬN VÀO BẢNG DIMENSION");
toolBox(s19, "Script:  run_classify_comment_aspect.py  (Step 2 — Aggregation)", 1.15);
// Flow
const aggSteps = [
  { t: "dim_video_comments\n(aspects JSONB)", c: BLUE2 },
  { t: "GROUP BY\nproduct_id, aspect", c: "1B7A4A" },
  { t: "UPDATE\ndim_*.user_review", c: "B8860B" },
];
aggSteps.forEach((st, i) => {
  const xp = 0.5 + i * 3.2;
  s19.addShape(pres.shapes.RECTANGLE, { x: xp, y: 1.85, w: 2.8, h: 0.9, fill: { color: CARD_BG }, line: { color: st.c, width: 1.5 } });
  s19.addText(st.t, { x: xp, y: 1.85, w: 2.8, h: 0.9, fontSize: 13, fontFace: "Calibri", color: WHITE, align: "center", valign: "middle", margin: 0 });
  if (i < 2) s19.addText("→", { x: xp + 2.8, y: 1.95, w: 0.4, h: 0.7, fontSize: 24, fontFace: "Calibri", color: CYAN, align: "center", valign: "middle", margin: 0 });
});
// Result format
card(s19, 0.5, 3.1, 9, 1.8);
s19.addText("Format user_review (JSON):", { x: 0.7, y: 3.15, w: 8, h: 0.35, fontSize: 14, fontFace: "Calibri", color: CYAN, bold: true, margin: 0 });
s19.addText("{\"total\": 42, \"comments\": [\"comment 1\", \"comment 2\", ...]}", { x: 0.7, y: 3.55, w: 8, h: 0.35, fontSize: 13, fontFace: "Consolas", color: GOLD, margin: 0 });
s19.addText("8 aspect → 8 bảng dimension tương ứng (display → dim_display, camera → dim_camera, ...)", { x: 0.7, y: 4.1, w: 8, h: 0.4, fontSize: 13, fontFace: "Calibri", color: MUTED, margin: 0 });

// ======= SLIDE 20 — EMBEDDING =======
let s20 = pres.addSlide(); bg(s20);
title(s20, "EMBEDDING DỮ LIỆU — VECTOR 768D");
s20.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.15, w: 9, h: 0.45, fill: { color: "0A2540" }, line: { color: GOLD, width: 1.2 } });
s20.addText("Model:  dangvantuan/vietnamese-embedding  (XLM-RoBERTa, 768D)", { x: 0.7, y: 1.15, w: 8.6, h: 0.45, fontSize: 13, fontFace: "Calibri", color: GOLD, bold: true, valign: "middle", margin: 0 });
// Comparison table
s20.addTable(tableRows(["Tiêu chí", "vietnamese-embedding", "MiniLM-L12-v2"], [
  ["Chiều vector", "768D", "384D"],
  ["Tiếng Việt", "Chuyên biệt (trained)", "Đa ngôn ngữ chung"],
  ["Chất lượng", "Cao", "Trung bình"],
  ["GPU", "Không cần", "Không cần"],
]), { x: 0.5, y: 1.85, w: 9, colW: [2.5, 3.25, 3.25], border: { pt: 0.5, color: "2C3E50" }, rowH: [0.4, 0.4, 0.4, 0.4, 0.4] });
// Pipeline flow
s20.addText("Pipeline:", { x: 0.5, y: 3.95, w: 1.2, h: 0.35, fontSize: 14, fontFace: "Calibri", color: CYAN, bold: true, margin: 0 });
const embSteps = ["pyvi\ntokenize", "Chunk\n(160 tokens)", "Sentence\nTransformer", "pgvector\n(768D)"];
embSteps.forEach((st, i) => {
  const xp = 1.7 + i * 2.1;
  s20.addShape(pres.shapes.RECTANGLE, { x: xp, y: 3.85, w: 1.8, h: 0.7, fill: { color: CARD_BG }, line: { color: BLUE2, width: 1 } });
  s20.addText(st, { x: xp, y: 3.85, w: 1.8, h: 0.7, fontSize: 11, fontFace: "Calibri", color: WHITE, align: "center", valign: "middle", margin: 0 });
  if (i < 3) s20.addText("→", { x: xp + 1.8, y: 3.95, w: 0.3, h: 0.5, fontSize: 18, fontFace: "Calibri", color: CYAN, align: "center", valign: "middle", margin: 0 });
});
s20.addText("Lưu trữ: PostgreSQL + pgvector  ·  Index: IVFFlat (cosine similarity)  ·  Batch: 512", { x: 0.5, y: 4.75, w: 9, h: 0.35, fontSize: 12, fontFace: "Calibri", color: MUTED, align: "center" });

// ======= SLIDE 21 — RAG ARCHITECTURE =======
let s21 = pres.addSlide(); bg(s21);
title(s21, "HỆ THỐNG RAG — KIẾN TRÚC TỔNG QUAN");
toolBox(s21, "Framework:  LangGraph (ReAct)  ·  Model: GPT-4o-mini  ·  Session: Redis (TTL 1800s)", 1.15);
// Architecture flow
const archBoxes = [
  { t: "User\nQuery", x: 0.3, c: BLUE2 },
  { t: "LangGraph\nReAct Agent", x: 2.55, c: "1B7A4A" },
  { t: "5 Tools", x: 4.8, c: "B8860B" },
  { t: "PostgreSQL\npgvector", x: 7.05, c: TBL_HDR },
];
archBoxes.forEach((b, i) => {
  s21.addShape(pres.shapes.RECTANGLE, { x: b.x, y: 1.95, w: 2.0, h: 1.0, fill: { color: CARD_BG }, line: { color: b.c, width: 1.5 } });
  s21.addText(b.t, { x: b.x, y: 1.95, w: 2.0, h: 1.0, fontSize: 14, fontFace: "Calibri", color: WHITE, bold: true, align: "center", valign: "middle", margin: 0 });
  if (i < 3) s21.addText("→", { x: b.x + 2.0, y: 2.1, w: 0.55, h: 0.7, fontSize: 24, fontFace: "Calibri", color: CYAN, align: "center", valign: "middle", margin: 0 });
});
// Response arrow
s21.addShape(pres.shapes.RECTANGLE, { x: 3.5, y: 3.3, w: 3, h: 0.5, fill: { color: CARD_BG }, line: { color: GOLD, width: 1 } });
s21.addText("←  Response (cited quotes)  →", { x: 3.5, y: 3.3, w: 3, h: 0.5, fontSize: 12, fontFace: "Calibri", color: GOLD, align: "center", valign: "middle", margin: 0 });
// Key features
s21.addText([
  { text: "ReAct pattern: Reasoning + Action loop tự động", options: { bullet: true, breakLine: true, color: WHITE, fontSize: 14 } },
  { text: "Trích dẫn chính xác từ bình luận thật (không hallucinate)", options: { bullet: true, breakLine: true, color: WHITE, fontSize: 14 } },
  { text: "Fallback \"không có dữ liệu\" khi thiếu comments", options: { bullet: true, color: WHITE, fontSize: 14 } },
], { x: 0.5, y: 4.05, w: 9, h: 1.2, fontFace: "Calibri", paraSpaceAfter: 4 });

// ======= SLIDE 22 — HyDE =======
let s22 = pres.addSlide(); bg(s22);
title(s22, "HyDE — HYPOTHETICAL DOCUMENT EMBEDDINGS");
toolBox(s22, "Paper: Gao et al. 2022  ·  Model: GPT-4o-mini  ·  K=5, temperature=0.9", 1.15);
// 4 steps
const hydeSteps = [
  { n: "1", t: "User query → GPT generates K=5 hypothetical YouTube comments (temp=0.9)" },
  { n: "2", t: "Encode hypothetical docs + original query bằng vietnamese-embedding" },
  { n: "3", t: "Mean-pool element-wise → composite query vector (Equation 8)" },
  { n: "4", t: "Cosine similarity search trên pgvector → top_k=20 kết quả" },
];
hydeSteps.forEach((st, i) => {
  const yy = 1.85 + i * 0.75;
  s22.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: yy, w: 0.45, h: 0.45, fill: { color: CYAN } });
  s22.addText(st.n, { x: 0.5, y: yy, w: 0.45, h: 0.45, fontSize: 16, fontFace: "Calibri", color: BG, bold: true, align: "center", valign: "middle", margin: 0 });
  s22.addText(st.t, { x: 1.15, y: yy, w: 8.3, h: 0.55, fontSize: 14, fontFace: "Calibri", color: WHITE, valign: "middle", margin: 0 });
});
s22.addText("HyDE cải thiện chất lượng retrieval bằng cách mở rộng query thành nhiều góc nhìn đa dạng", { x: 0.5, y: 4.9, w: 9, h: 0.35, fontSize: 12, fontFace: "Calibri", color: GOLD, italic: true, align: "center" });

// ======= SLIDE 23 — 5 TOOLS =======
let s23 = pres.addSlide(); bg(s23);
title(s23, "5 CÔNG CỤ CỦA RAG AGENT");
s23.addTable(tableRows(["Tool", "Chức năng", "Kỹ thuật"], [
  ["search_product", "Tìm sản phẩm theo tên", "Fuzzy search (similarity > 0.1)"],
  ["get_all_specs", "Lấy toàn bộ specs", "JOIN 8 dim tables"],
  ["get_product_specs", "Specs theo khía cạnh cụ thể", "Query dim cụ thể"],
  ["get_comments", "Tìm bình luận liên quan", "HyDE + pgvector (top_k=20)"],
  ["list_products", "Lọc theo brand/giá", "ILIKE + price filter"],
]), { x: 0.5, y: 1.15, w: 9, colW: [2.5, 3, 3.5], border: { pt: 0.5, color: "2C3E50" }, rowH: [0.45, 0.55, 0.55, 0.55, 0.55, 0.55] });
s23.addText("Agent tự động chọn tool phù hợp dựa trên ngữ cảnh câu hỏi (ReAct reasoning loop)", { x: 0.5, y: 4.6, w: 9, h: 0.4, fontSize: 13, fontFace: "Calibri", color: MUTED, italic: true, align: "center" });

// ======= SLIDE 24 — SYSTEM PROMPT & SESSION =======
let s24 = pres.addSlide(); bg(s24);
title(s24, "SYSTEM PROMPT & QUẢN LÝ PHIÊN");
// Left
card(s24, 0.5, 1.2, 4.3, 3.5);
s24.addText("System Prompt Rules", { x: 0.7, y: 1.25, w: 3.9, h: 0.4, fontSize: 15, fontFace: "Calibri", color: CYAN, bold: true, margin: 0 });
s24.addText([
  { text: "Trích dẫn chính xác từ bình luận thật", options: { bullet: true, breakLine: true, color: WHITE, fontSize: 14 } },
  { text: "Lọc theo aspect cụ thể được hỏi", options: { bullet: true, breakLine: true, color: WHITE, fontSize: 14 } },
  { text: "Fallback \"không có dữ liệu\" khi thiếu", options: { bullet: true, breakLine: true, color: WHITE, fontSize: 14 } },
  { text: "Không hallucinate — chỉ dùng dữ liệu thật", options: { bullet: true, color: WHITE, fontSize: 14 } },
], { x: 0.7, y: 1.75, w: 3.9, h: 2.5, fontFace: "Calibri", paraSpaceAfter: 8 });
// Right
card(s24, 5.2, 1.2, 4.3, 3.5);
s24.addText("Session Management", { x: 5.4, y: 1.25, w: 3.9, h: 0.4, fontSize: 15, fontFace: "Calibri", color: CYAN, bold: true, margin: 0 });
s24.addText([
  { text: "Redis-based TTL: 1800s (30 phút)", options: { bullet: true, breakLine: true, color: WHITE, fontSize: 14 } },
  { text: "MemorySaver checkpointer", options: { bullet: true, breakLine: true, color: WHITE, fontSize: 14 } },
  { text: "Auto-reset sau inactivity", options: { bullet: true, breakLine: true, color: WHITE, fontSize: 14 } },
  { text: "Thread ID resolution tự động", options: { bullet: true, color: WHITE, fontSize: 14 } },
], { x: 5.4, y: 1.75, w: 3.9, h: 2.5, fontFace: "Calibri", paraSpaceAfter: 8 });

// ======= SLIDE 25 — TỔNG KẾT =======
let s25 = pres.addSlide(); bg(s25);
title(s25, "TỔNG KẾT KẾT QUẢ ĐẠT ĐƯỢC");
const achievements = [
  { title: "Pipeline hoàn chỉnh", desc: "10 bước từ crawl đến embedding, tự động hóa", accent: CYAN },
  { title: "Star Schema", desc: "1 Fact + 8 Dimension + 2 YouTube + 1 Embedding", accent: BLUE2 },
  { title: "RAG Agent", desc: "HyDE retrieval + 5 tools + trích dẫn bình luận thật", accent: "1B7A4A" },
  { title: "Production-ready", desc: "AWS S3, PostgreSQL RDS, Redis, Docker", accent: GOLD },
];
achievements.forEach((a, i) => {
  const col = i % 2;
  const row = Math.floor(i / 2);
  const xp = 0.5 + col * 4.65;
  const yp = 1.2 + row * 1.8;
  card(s25, xp, yp, 4.35, 1.5);
  s25.addShape(pres.shapes.RECTANGLE, { x: xp, y: yp, w: 0.08, h: 1.5, fill: { color: a.accent } });
  s25.addText(a.title, { x: xp + 0.25, y: yp + 0.15, w: 3.9, h: 0.4, fontSize: 17, fontFace: "Calibri", color: GOLD, bold: true, margin: 0 });
  s25.addText(a.desc, { x: xp + 0.25, y: yp + 0.65, w: 3.9, h: 0.6, fontSize: 14, fontFace: "Calibri", color: WHITE, margin: 0 });
});

// ======= SLIDE 26 — KẾT QUẢ CHI TIẾT =======
let s26 = pres.addSlide(); bg(s26);
title(s26, "KẾT QUẢ CHI TIẾT");
s26.addTable(tableRows(["Hạng mục", "Kết quả"], [
  ["Sản phẩm thu thập", "~1,500+ smartphone"],
  ["Bình luận YouTube", "12,800+ comments"],
  ["Video YouTube", "Hàng nghìn video review"],
  ["Bảng dữ liệu", "12 bảng (Star Schema)"],
  ["Vector embeddings", "768D, pgvector IVFFlat"],
  ["RAG Agent tools", "5 tools, GPT-4o-mini"],
  ["Lưu trữ", "AWS S3 + PostgreSQL RDS"],
]), { x: 1, y: 1.15, w: 8, colW: [3.5, 4.5], border: { pt: 0.5, color: "2C3E50" }, rowH: [0.45, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5] });

// ======= SLIDE 27 — HẠN CHẾ =======
let s27 = pres.addSlide(); bg(s27);
title(s27, "HẠN CHẾ");
const limitations = [
  { t: "Nguồn dữ liệu giới hạn 1 website (MobileCity) — chưa đa nguồn", icon: "1" },
  { t: "Phân loại comment dựa trên keyword — chưa dùng deep learning classifier", icon: "2" },
  { t: "Chưa có evaluation benchmark cho RAG response quality", icon: "3" },
  { t: "YouTube API quota giới hạn — cần nhiều API key để scale", icon: "4" },
];
limitations.forEach((l, i) => {
  const yy = 1.3 + i * 0.95;
  card(s27, 0.5, yy, 9, 0.75);
  s27.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: yy, w: 0.55, h: 0.75, fill: { color: "8B0000" } });
  s27.addText(l.icon, { x: 0.5, y: yy, w: 0.55, h: 0.75, fontSize: 18, fontFace: "Calibri", color: WHITE, bold: true, align: "center", valign: "middle", margin: 0 });
  s27.addText(l.t, { x: 1.25, y: yy, w: 8, h: 0.75, fontSize: 15, fontFace: "Calibri", color: WHITE, valign: "middle", margin: 0 });
});

// ======= SLIDE 28 — HƯỚNG PHÁT TRIỂN =======
let s28 = pres.addSlide(); bg(s28);
title(s28, "HƯỚNG PHÁT TRIỂN TƯƠNG LAI");
const futures = [
  { t: "Mở rộng nguồn crawl (TGDD, CellphoneS, FPT Shop)", color: CYAN },
  { t: "Deep learning classifier thay thế keyword matching", color: BLUE2 },
  { t: "Fine-tune embedding model trên dữ liệu tiếng Việt domain-specific", color: "1B7A4A" },
  { t: "Xây dựng UI/UX hoàn chỉnh & deploy production", color: GOLD },
];
futures.forEach((f, i) => {
  const yy = 1.3 + i * 0.95;
  card(s28, 0.5, yy, 9, 0.75);
  s28.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: yy, w: 0.55, h: 0.75, fill: { color: f.color } });
  s28.addText(String(i + 1), { x: 0.5, y: yy, w: 0.55, h: 0.75, fontSize: 18, fontFace: "Calibri", color: BG, bold: true, align: "center", valign: "middle", margin: 0 });
  s28.addText(f.t, { x: 1.25, y: yy, w: 8, h: 0.75, fontSize: 15, fontFace: "Calibri", color: WHITE, valign: "middle", margin: 0 });
});

// ======= SLIDE 29 — CẢM ƠN =======
let s29 = pres.addSlide();
s29.background = { color: "081529" };
s29.addShape(pres.shapes.LINE, { x: 2, y: 1.5, w: 6, h: 0, line: { color: CYAN, width: 1 } });
s29.addText("CẢM ƠN THẦY/CÔ & CÁC BẠN\nĐÃ LẮNG NGHE!", { x: 0.5, y: 1.6, w: 9, h: 1.5, fontSize: 30, fontFace: "Calibri", color: WHITE, bold: true, align: "center", valign: "middle", lineSpacingMultiple: 1.3 });
s29.addShape(pres.shapes.LINE, { x: 2, y: 3.2, w: 6, h: 0, line: { color: CYAN, width: 1 } });
s29.addText("Đồ án DS200 — Big Data", { x: 0.5, y: 3.3, w: 9, h: 0.5, fontSize: 18, fontFace: "Calibri", color: MUTED, italic: true, align: "center" });
s29.addText("Q & A", { x: 3, y: 3.9, w: 4, h: 0.8, fontSize: 40, fontFace: "Calibri", color: CYAN, bold: true, align: "center", valign: "middle" });
s29.addText("[email placeholder]", { x: 0.5, y: 4.9, w: 9, h: 0.3, fontSize: 12, fontFace: "Calibri", color: MUTED, align: "center" });

// ======= WRITE =======
pres.writeFile({ fileName: "E:\\DS200_Do_an\\DS200_Big_Data\\DS200_Presentation.pptx" })
  .then(() => console.log("OK: DS200_Presentation.pptx created"))
  .catch(err => console.error("Error:", err));
