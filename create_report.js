const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, BorderStyle, WidthType, ShadingType,
  HeadingLevel, PageBreak
} = require("docx");

const BLUE = "2E5090";
const LIGHT_BLUE = "D6E4F0";
const LIGHT_GREEN = "E2EFDA";
const LIGHT_ORANGE = "FCE4D6";
const LIGHT_YELLOW = "FFF2CC";
const GRAY_BORDER = "BBBBBB";
const border = { style: BorderStyle.SINGLE, size: 1, color: GRAY_BORDER };
const borders = { top: border, bottom: border, left: border, right: border };
const cellMargins = { top: 50, bottom: 50, left: 80, right: 80 };

const CONTENT_W = 9026;

function headerCell(text, width) {
  return new TableCell({
    borders, width: { size: width, type: WidthType.DXA },
    shading: { fill: LIGHT_BLUE, type: ShadingType.CLEAR },
    margins: cellMargins, verticalAlign: "center",
    children: [new Paragraph({ spacing: { before: 30, after: 30 }, children: [new TextRun({ text, bold: true, font: "Calibri", size: 20 })] })]
  });
}

function colorHeaderCell(text, width, fill) {
  return new TableCell({
    borders, width: { size: width, type: WidthType.DXA },
    shading: { fill, type: ShadingType.CLEAR },
    margins: cellMargins, verticalAlign: "center",
    children: [new Paragraph({ spacing: { before: 30, after: 30 }, children: [new TextRun({ text, bold: true, font: "Calibri", size: 20 })] })]
  });
}

function dataCell(text, width, opts = {}) {
  const runs = parseRuns(text, 20, opts.italic);
  return new TableCell({
    borders, width: { size: width, type: WidthType.DXA },
    margins: cellMargins,
    shading: opts.fill ? { fill: opts.fill, type: ShadingType.CLEAR } : undefined,
    children: [new Paragraph({ spacing: { before: 30, after: 30 }, children: runs })]
  });
}

function multiLineDataCell(lines, width, opts = {}) {
  return new TableCell({
    borders, width: { size: width, type: WidthType.DXA },
    margins: cellMargins,
    children: lines.map(l => new Paragraph({ spacing: { before: 20, after: 20 }, children: parseRuns(l, 20) }))
  });
}

function parseRuns(text, size, italic) {
  const runs = [];
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  parts.forEach(p => {
    if (p.startsWith("**") && p.endsWith("**")) {
      runs.push(new TextRun({ text: p.slice(2, -2), bold: true, font: "Calibri", size, italics: italic }));
    } else if (p) {
      runs.push(new TextRun({ text: p, font: "Calibri", size, italics: italic }));
    }
  });
  return runs;
}

function bodyText(text, opts = {}) {
  return new Paragraph({
    spacing: { before: opts.before || 60, after: opts.after || 60 },
    alignment: opts.align || AlignmentType.LEFT,
    indent: opts.indent ? { left: opts.indent } : undefined,
    children: parseRuns(text, 22, opts.italic)
  });
}

function smallText(text, opts = {}) {
  return new Paragraph({
    spacing: { before: opts.before || 40, after: opts.after || 40 },
    alignment: opts.align || AlignmentType.LEFT,
    indent: opts.indent ? { left: opts.indent } : undefined,
    children: parseRuns(text, 20, opts.italic)
  });
}

function bulletItem(text, ref, level) {
  return new Paragraph({
    numbering: { reference: ref, level: level || 0 },
    spacing: { before: 30, after: 30 },
    children: parseRuns(text, 21)
  });
}

function numberedItem(text, ref, level) {
  return new Paragraph({
    numbering: { reference: ref, level: level || 0 },
    spacing: { before: 30, after: 30 },
    children: parseRuns(text, 21)
  });
}

function subHeading(text) {
  return new Paragraph({
    spacing: { before: 180, after: 80 },
    children: [new TextRun({ text, bold: true, font: "Calibri", size: 24 })]
  });
}

function subSubHeading(text) {
  return new Paragraph({
    spacing: { before: 140, after: 60 },
    children: [new TextRun({ text, bold: true, font: "Calibri", size: 22, color: "404040" })]
  });
}

function stageHeading(text) {
  return new Paragraph({
    spacing: { before: 260, after: 160 },
    children: [new TextRun({ text, bold: true, font: "Calibri", size: 28, color: BLUE })]
  });
}

function sectionLine() {
  return new Paragraph({
    spacing: { before: 80, after: 80 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: BLUE, space: 4 } },
    children: []
  });
}

const doc = new Document({
  numbering: {
    config: [
      { reference: "bullets", levels: [
        { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
        { level: 1, format: LevelFormat.BULLET, text: "◦", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 1080, hanging: 360 } } } }
      ]},
      { reference: "n_crawl", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "n_process", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "n_yt", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "n_db", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "n_embed", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "n_reason", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "n_dim", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 1080, hanging: 360 } } } }] },
      { reference: "n_design", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    },
    children: [
      // ===== TITLE =====
      new Paragraph({ spacing: { before: 400, after: 0 }, children: [] }),
      new Paragraph({ spacing: { before: 160, after: 60 }, alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "BÁO CÁO TỔNG HỢP", bold: true, font: "Calibri", size: 36, color: BLUE })] }),
      new Paragraph({ spacing: { before: 0, after: 60 }, alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "QUY TRÌNH XÂY DỰNG HỆ THỐNG DỮ LIỆU", bold: true, font: "Calibri", size: 36, color: BLUE })] }),
      new Paragraph({ spacing: { before: 160, after: 40 }, alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "Đồ án DS200 — Big Data", font: "Calibri", size: 24, italics: true })] }),
      new Paragraph({ spacing: { before: 40, after: 160 }, alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "Tháng 6/2026", font: "Calibri", size: 22 })] }),
      sectionLine(),

      // ===== STAGE 1 =====
      stageHeading("STAGE 1: THIẾT KẾ CƠ SỞ DỮ LIỆU & QUY TRÌNH XỬ LÝ DỮ LIỆU"),

      // =============================================
      // SECTION 1: TỔNG QUAN PIPELINE
      // =============================================
      subHeading("1. Tổng quan pipeline dữ liệu"),
      bodyText("Toàn bộ hệ thống dữ liệu được xây dựng qua **7 giai đoạn** tuần tự, từ thu thập dữ liệu thô đến lưu trữ vector cho semantic search:"),

      // Pipeline overview table
      new Table({
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [600, 2200, 3226, 3000],
        rows: [
          new TableRow({ children: [
            headerCell("TT", 600), headerCell("Giai đoạn", 2200),
            headerCell("Mô tả", 3226), headerCell("Đầu ra", 3000)
          ]}),
          new TableRow({ children: [
            dataCell("1", 600), dataCell("**Crawling**", 2200),
            dataCell("Cào link sản phẩm & thông số kỹ thuật từ MobileCity", 3226),
            dataCell("product_links.json, all_product_specs_raw.json", 3000)
          ]}),
          new TableRow({ children: [
            dataCell("2", 600), dataCell("**Data Processing**", 2200),
            dataCell("Khử trùng lặp + Chuẩn hóa tên bằng LLM", 3226),
            dataCell("final_ready_to_load_specs.json", 3000)
          ]}),
          new TableRow({ children: [
            dataCell("3", 600), dataCell("**Database Loading**", 2200),
            dataCell("Tạo schema & nạp dữ liệu vào PostgreSQL (RDS)", 3226),
            dataCell("fact_product + 8 dim tables", 3000)
          ]}),
          new TableRow({ children: [
            dataCell("4", 600), dataCell("**YouTube Media**", 2200),
            dataCell("Tìm video, tải audio/comments/transcripts", 3226),
            dataCell("S3 buckets + dim_video_*", 3000)
          ]}),
          new TableRow({ children: [
            dataCell("5", 600), dataCell("**S3 Upload**", 2200),
            dataCell("Đẩy file media lên AWS S3 theo cấu trúc thư mục", 3226),
            dataCell("s3://smartphone-data-s3/", 3000)
          ]}),
          new TableRow({ children: [
            dataCell("6", 600), dataCell("**Aspect Classification**", 2200),
            dataCell("Phân loại comment theo bộ vocab → gom vào dimension tương ứng", 3226),
            dataCell("dim_*.user_review (JSON)", 3000)
          ]}),
          new TableRow({ children: [
            dataCell("7", 600), dataCell("**Embedding**", 2200),
            dataCell("Vector hóa bình luận để semantic search", 3226),
            dataCell("comment_embeddings (pgvector)", 3000)
          ]}),
        ]
      }),

      sectionLine(),

      // =============================================
      // SECTION 2: CHI TIẾT CRAWLING
      // =============================================
      subHeading("2. Giai đoạn 1: Thu thập dữ liệu (Crawling)"),

      subSubHeading("2.1. Cào danh sách link sản phẩm"),
      bodyText("**Script:** run_crawl_product_links.py"),
      bulletItem("**Nguồn:** Website MobileCity — cào tất cả category slugs và trang danh sách sản phẩm", "bullets"),
      bulletItem("**Kỹ thuật:** requests + BeautifulSoup, có pagination và retry, throttle sleep(0.8s) giữa các request", "bullets"),
      bulletItem("**Cấu hình:** mobilecity_cookie, mobilecity_csrf_token, max_pages_per_slug = 60", "bullets"),
      bulletItem("**Đầu ra:** data/raw/product_links.json", "bullets"),
      smallText("Format: [{product_name, url, price_vnd, price_str, image, slug}, ...]", { indent: 720, italic: true }),

      subSubHeading("2.2. Cào thông số kỹ thuật chi tiết"),
      bodyText("**Script:** run_crawl_all_specs.py"),
      bulletItem("**Đầu vào:** data/raw/product_links.json (danh sách URL từ bước 2.1)", "bullets"),
      bulletItem("**Xử lý:** Truy cập từng URL sản phẩm, parse bảng thông số kỹ thuật bằng BeautifulSoup", "bullets"),
      bulletItem("**Mapping:** Tự động ánh xạ tên trường tiếng Việt sang schema database (fact + 8 dimensions)", "bullets"),
      bulletItem("**An toàn:** Checkpoint mỗi 50 bản ghi để tránh mất dữ liệu", "bullets"),
      bulletItem("**Đầu ra:** data/raw/all_product_specs_raw.json", "bullets"),
      smallText("Format: [{_source_url, fact_product: {...}, dim_display: {...}, dim_camera: {...}, ...8 dims}, ...]", { indent: 720, italic: true }),

      // Fields table
      bodyText("**Các trường được cào theo từng dimension:**", { before: 100 }),
      new Table({
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [2400, 6626],
        rows: [
          new TableRow({ children: [headerCell("Bảng", 2400), headerCell("Các trường dữ liệu", 6626)] }),
          new TableRow({ children: [dataCell("fact_product", 2400), dataCell("product_name, os_version, language_support", 6626)] }),
          new TableRow({ children: [dataCell("dim_display", 2400), dataCell("display_type, color_depth, display_standard, resolution, screen_size, touch_technology", 6626)] }),
          new TableRow({ children: [dataCell("dim_camera", 2400), dataCell("rear_camera, front_camera, flash_light, camera_features, video_recording, video_call", 6626)] }),
          new TableRow({ children: [dataCell("dim_performance", 2400), dataCell("cpu_speed, core_count, chipset, ram_capacity, gpu_chip", 6626)] }),
          new TableRow({ children: [dataCell("dim_storage", 2400), dataCell("phonebook_storage, internal_storage, external_memory, max_external_support", 6626)] }),
          new TableRow({ children: [dataCell("dim_design", 2400), dataCell("design_style, dimensions, weight", 6626)] }),
          new TableRow({ children: [dataCell("dim_battery", 2400), dataCell("battery_type, battery_capacity, removable_battery", 6626)] }),
          new TableRow({ children: [dataCell("dim_connectivity", 2400), dataCell("network_3g/4g, sim_type/slots, wifi, gps, bluetooth, nfc, usb, charging_port, ...", 6626)] }),
          new TableRow({ children: [dataCell("dim_utilities", 2400), dataCell("movie_playback, music_playback, voice_recorder, fm_radio, other_features", 6626)] }),
        ]
      }),

      sectionLine(),

      // =============================================
      // SECTION 3: DATA PROCESSING
      // =============================================
      subHeading("3. Giai đoạn 2: Tiền xử lý dữ liệu (Data Processing)"),

      subSubHeading("3.1. Khử trùng lặp dựa trên phần cứng (Hardware-based Deduplication)"),
      bodyText("**Script:** run_deduplicate_specs.py"),
      bodyText("**Đầu vào:** data/raw/all_product_specs_raw.json"),
      bodyText("**Quy trình:**"),
      numberedItem("Nhóm các bản ghi theo **MD5 hash** của 7 thuộc tính phần cứng bất biến:", "n_process"),

      // 7 fields table
      new Table({
        width: { size: 7500, type: WidthType.DXA },
        columnWidths: [600, 2400, 4500],
        rows: [
          new TableRow({ children: [headerCell("#", 600), headerCell("Trường", 2400), headerCell("Bảng nguồn", 4500)] }),
          new TableRow({ children: [dataCell("1", 600), dataCell("chipset", 2400), dataCell("dim_performance", 4500)] }),
          new TableRow({ children: [dataCell("2", 600), dataCell("core_count", 2400), dataCell("dim_performance", 4500)] }),
          new TableRow({ children: [dataCell("3", 600), dataCell("ram_capacity", 2400), dataCell("dim_performance", 4500)] }),
          new TableRow({ children: [dataCell("4", 600), dataCell("gpu_chip", 2400), dataCell("dim_performance", 4500)] }),
          new TableRow({ children: [dataCell("5", 600), dataCell("dimensions", 2400), dataCell("dim_design", 4500)] }),
          new TableRow({ children: [dataCell("6", 600), dataCell("weight", 2400), dataCell("dim_design", 4500)] }),
          new TableRow({ children: [dataCell("7", 600), dataCell("battery_capacity", 2400), dataCell("dim_battery", 4500)] }),
        ]
      }),

      numberedItem("Chọn bản ghi **Master** trong mỗi nhóm (tên sản phẩm ngắn nhất)", "n_process"),
      numberedItem("Gán ID duy nhất: **DEV-{MD5_HASH_PREFIX:10}**", "n_process"),
      numberedItem("Đánh dấu các bản ghi trùng bằng trường reference_id", "n_process"),

      bodyText("**Đầu ra:**"),
      bulletItem("data/processed/**unique_smartphone_specs.json** (bản ghi Master, có id)", "bullets"),
      bulletItem("data/processed/**suspected_duplicates.json** (các bản ghi trùng, có reference_id)", "bullets"),

      bodyText("**Lý do dùng phần cứng:** Thuộc tính phần cứng là **bất biến** (không thay đổi theo chiến dịch marketing), trong khi tên sản phẩm thường bị thay đổi bởi nhà bán lẻ.", { italic: true }),

      subSubHeading("3.2. Chuẩn hóa tên bằng LLM (LLM Name Normalization)"),
      bodyText("**Script:** run_llm_name_normalization.py"),
      bodyText("**Đầu vào:** data/processed/unique_smartphone_specs.json"),
      bodyText("**Quy trình:**"),
      numberedItem("Gửi cho OpenAI GPT (temperature=0.1 để đảm bảo tính nhất quán) 3 trường: product_name, chipset, internal_storage", "n_process"),
      numberedItem("LLM sinh ra trường **search_query_name** chuẩn hóa (chỉ giữ: Brand + Model + Chipset)", "n_process"),
      numberedItem("Loại bỏ: text marketing, chỉ báo tình trạng (mới/cũ), biến thể vùng, chi tiết dung lượng", "n_process"),
      numberedItem("Rate limiting: tự động lưu mỗi 100 mẫu, sleep 30s giữa các batch", "n_process"),
      bodyText("**Đầu ra:** data/processed/**ready_to_load_specs.json** (tất cả fields + search_query_name mới)"),

      subSubHeading("3.3. Khử trùng lặp lần cuối (Final Deduplication)"),
      bodyText("**Script:** run_final_deduplication.py"),
      bodyText("**Đầu vào:** data/processed/ready_to_load_specs.json"),
      bulletItem("Loại bỏ các bản ghi có **search_query_name trùng nhau** (giữ lần xuất hiện đầu tiên)", "bullets"),
      bodyText("**Đầu ra:** data/processed/**final_ready_to_load_specs.json** (đã sẵn sàng nạp vào DB)"),

      sectionLine(),

      // =============================================
      // SECTION 4: DATABASE LOADING
      // =============================================
      subHeading("4. Giai đoạn 3: Nạp dữ liệu vào RDS (Database Loading)"),

      subSubHeading("4.1. Khởi tạo schema (Bootstrap)"),
      bodyText("**Script:** bootstrap_db.py"),
      bulletItem("Thực thi SQLAlchemy **metadata.create_all()** để tạo toàn bộ bảng", "bullets"),
      bulletItem("Schema được định nghĩa trong **models.py** (SQLAlchemy ORM)", "bullets"),
      bulletItem("Kết nối: PostgreSQL (RDS) tại db_host:db_port/db_name", "bullets"),

      subSubHeading("4.2. Nạp dữ liệu sản phẩm (Load Products)"),
      bodyText("**Script:** load_products_to_db.py"),
      bodyText("**Đầu vào:**"),
      bulletItem("data/processed/**final_ready_to_load_specs.json** (thông số kỹ thuật)", "bullets"),
      bulletItem("data/raw/**product_links.json** (giá & URL hình ảnh)", "bullets"),

      bodyText("**Quy trình nạp từng bản ghi:**"),
      numberedItem("Tạo index từ product_links.json theo URL để tra cứu nhanh giá/hình", "n_db"),
      numberedItem("INSERT vào **fact_product** (lấy product_id tự động tăng)", "n_db"),
      numberedItem("INSERT vào **8 bảng dimension** với FK trỏ về product_id", "n_db"),
      numberedItem("Bỏ qua: bản ghi lỗi hoặc product_name đã tồn tại", "n_db"),
      bodyText("**ACID compliance:** Sử dụng SQLAlchemy transactions đảm bảo toàn vẹn dữ liệu."),
      bodyText("**Chế độ chạy:** --truncate (xóa sạch & nạp lại) hoặc --append (chỉ thêm mới)"),

      subSubHeading("4.3. Cấu trúc Star Schema trong RDS"),
      bodyText("Hệ thống sử dụng **Star Schema** với 1 bảng Fact trung tâm và 8 bảng Dimension:"),

      // Star schema table
      new Table({
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [2600, 3213, 3213],
        rows: [
          new TableRow({ children: [headerCell("Bảng", 2600), headerCell("Vai trò", 3213), headerCell("Cột chính", 3213)] }),
          new TableRow({ children: [
            dataCell("**fact_product**", 2600, { fill: LIGHT_ORANGE }),
            dataCell("Hub trung tâm — nhận dạng sản phẩm", 3213),
            dataCell("product_id (PK), product_name, price, os_version, picture_url, created_at", 3213)
          ]}),
          new TableRow({ children: [
            dataCell("**dim_display**", 2600), dataCell("Thông số màn hình", 3213),
            dataCell("display_type, resolution, screen_size, touch_technology, ...", 3213)
          ]}),
          new TableRow({ children: [
            dataCell("**dim_camera**", 2600), dataCell("Thông số camera", 3213),
            dataCell("rear_camera, front_camera, flash, video_recording, ...", 3213)
          ]}),
          new TableRow({ children: [
            dataCell("**dim_performance**", 2600), dataCell("Hiệu năng xử lý", 3213),
            dataCell("chipset, cpu_speed, core_count, ram_capacity, gpu_chip", 3213)
          ]}),
          new TableRow({ children: [
            dataCell("**dim_storage**", 2600), dataCell("Bộ nhớ", 3213),
            dataCell("internal_storage, external_memory, max_external_support", 3213)
          ]}),
          new TableRow({ children: [
            dataCell("**dim_design**", 2600), dataCell("Thiết kế vật lý", 3213),
            dataCell("design_style, dimensions, weight", 3213)
          ]}),
          new TableRow({ children: [
            dataCell("**dim_battery**", 2600), dataCell("Pin", 3213),
            dataCell("battery_type, battery_capacity, removable_battery", 3213)
          ]}),
          new TableRow({ children: [
            dataCell("**dim_connectivity**", 2600), dataCell("Kết nối", 3213),
            dataCell("wifi, bluetooth, nfc, sim_type, gps, usb, charging_port, ...", 3213)
          ]}),
          new TableRow({ children: [
            dataCell("**dim_utilities**", 2600), dataCell("Tiện ích", 3213),
            dataCell("movie_playback, music_playback, fm_radio, other_features", 3213)
          ]}),
        ]
      }),

      bodyText("Mỗi bảng dimension đều có thêm: **dim_id** (PK), **product_id** (FK), **youtuber_review** (JSON), **user_review** (JSON), **last_updated** (timestamp).", { before: 80 }),

      bodyText("**Nguyên tắc thiết kế:**"),
      numberedItem("**Phân tách theo khía cạnh** — Mỗi dimension = 1 khía cạnh phần cứng riêng biệt", "n_design"),
      numberedItem("**Truy vấn độc lập** — Không cần JOIN toàn bộ 8 bảng khi chỉ cần 1 khía cạnh", "n_design"),
      numberedItem("**Tối ưu phân tích** — Nhà phân tích tập trung vào đúng dữ liệu cần thiết", "n_design"),
      numberedItem("**Mở rộng dễ dàng** — Thêm dimension mới không ảnh hưởng các bảng hiện tại", "n_design"),

      sectionLine(),

      // =============================================
      // SECTION 5: YOUTUBE MEDIA + S3
      // =============================================
      subHeading("5. Giai đoạn 4: Thu thập YouTube Media & Đẩy lên S3"),

      subSubHeading("5.1. Tìm kiếm video YouTube"),
      bodyText("**Script:** run_unique_smartphone_media_flow.py"),
      numberedItem("Gọi **YouTube Data API** với query: \"review {product_name}\", regionCode=\"VN\"", "n_yt"),
      numberedItem("Sử dụng **API Key Pool** (thread-safe): tự động xoay vòng khi hết quota (HTTP 403)", "n_yt"),
      numberedItem("Cấu hình: max_results = 30/product, min_videos = 25/product", "n_yt"),

      subSubHeading("5.2. Tải media về local (tạm thời)"),
      bodyText("**3 luồng tải song song** cho mỗi video:"),

      new Table({
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [1800, 2413, 2413, 2400],
        rows: [
          new TableRow({ children: [
            headerCell("Loại", 1800), headerCell("Công cụ", 2413),
            headerCell("Output", 2413), headerCell("Đường dẫn tạm", 2400)
          ]}),
          new TableRow({ children: [
            dataCell("**Audio**", 1800), dataCell("yt-dlp (-x --audio-format mp3)", 2413),
            dataCell("{title}.mp3", 2413), dataCell("data/processed/youtube_media/audio/{product}/", 2400)
          ]}),
          new TableRow({ children: [
            dataCell("**Comments**", 1800), dataCell("yt-dlp (--write-comments)", 2413),
            dataCell("{title}_comments.csv", 2413), dataCell("data/processed/youtube_media/comments/{product}/", 2400)
          ]}),
          new TableRow({ children: [
            dataCell("**Transcript**", 1800), dataCell("youtube-transcript-api", 2413),
            dataCell("{title}_transcript.json", 2413), dataCell("data/processed/youtube_media/transcripts/{product}/", 2400)
          ]}),
        ]
      }),

      bodyText("**Transcript language priority:** vi > en > bất kỳ ngôn ngữ nào (bao gồm auto-generated)"),
      bodyText("**Đa luồng:** ThreadPoolExecutor với 3 workers, mỗi product xử lý trong thread riêng (thread-safe tracking)"),

      subSubHeading("5.3. Upload lên AWS S3"),
      bodyText("**S3 Bucket:** s3://smartphone-data-s3/ (region: ap-southeast-1)"),
      bodyText("**Cấu trúc thư mục S3:**"),

      new Table({
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [1400, 4626, 3000],
        rows: [
          new TableRow({ children: [
            colorHeaderCell("Prefix", 1400, LIGHT_GREEN), colorHeaderCell("S3 Key Pattern", 4626, LIGHT_GREEN),
            colorHeaderCell("Nội dung", 3000, LIGHT_GREEN)
          ]}),
          new TableRow({ children: [
            dataCell("**audio/**", 1400), dataCell("audio/{safe_product_name}/{video_id}_audio.mp3", 4626),
            dataCell("File audio MP3 của video review", 3000)
          ]}),
          new TableRow({ children: [
            dataCell("**comments/**", 1400), dataCell("comments/{safe_product_name}/{video_id}_comments.csv", 4626),
            dataCell("Bình luận người dùng (CSV)", 3000)
          ]}),
          new TableRow({ children: [
            dataCell("**transcripts/**", 1400), dataCell("transcripts/{safe_product_name}/{video_id}_transcript.json", 4626),
            dataCell("Transcript video (JSON)", 3000)
          ]}),
          new TableRow({ children: [
            dataCell("**media_log/**", 1400), dataCell("media_log/{YYYY-MM-DD}/{product_name}.log", 4626),
            dataCell("Log quá trình xử lý", 3000)
          ]}),
        ]
      }),

      bodyText("**Quy tắc đặt tên S3 key:**"),
      bulletItem("Product name: lowercase, loại bỏ ký tự đặc biệt, thay bằng \"_\", strip underscores thừa", "bullets"),
      bulletItem("Storage ID: YouTube video ID", "bullets"),
      bulletItem("Sử dụng hàm: build_audio_key(), build_comments_key(), build_transcript_key()", "bullets"),

      bodyText("**Quy trình upload:**"),
      numberedItem("Tải file về thư mục tạm local (data/processed/youtube_media/)", "n_yt"),
      numberedItem("Gọi upload_audio_file() / upload_comments_file() / upload_transcript_file()", "n_yt"),
      numberedItem("Nhận về đường dẫn S3 đầy đủ (s3://bucket/key)", "n_yt"),
      numberedItem("**Xóa file tạm** sau khi upload thành công", "n_yt"),
      numberedItem("Log được flush lên S3: mỗi 10 dòng, ngay khi ERROR/CRITICAL, và trước khi exit", "n_yt"),

      subSubHeading("5.4. Lưu metadata vào RDS"),
      bodyText("Sau khi upload S3, metadata được ghi vào 2 bảng:"),

      new Table({
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [2800, 6226],
        rows: [
          new TableRow({ children: [headerCell("Bảng", 2800), headerCell("Dữ liệu lưu trữ", 6226)] }),
          new TableRow({ children: [
            dataCell("**dim_video_transcripts**", 2800),
            dataCell("video_id (PK), product_id (FK), youtube_url (UNIQUE), s3_audio_path, s3_transcript_path, s3_comments_path, raw_transcript, created_at", 6226)
          ]}),
          new TableRow({ children: [
            dataCell("**dim_video_comments**", 2800),
            dataCell("comment_id (PK), video_id (FK → dim_video_transcripts), user_name, comment_text, created_at", 6226)
          ]}),
        ]
      }),

      bodyText("**Liên kết:** dim_video_transcripts.product_id → fact_product.product_id → 8 dim tables", { italic: true }),

      sectionLine(),

      // =============================================
      // SECTION 6: COMMENT CLASSIFICATION
      // =============================================
      subHeading("6. Giai đoạn 5: Phân loại bình luận theo khía cạnh (Aspect Classification)"),

      bodyText("Trước khi tiến hành embedding, hệ thống cần **phân loại từng bình luận** thuộc về khía cạnh nào (camera, pin, hiệu năng...) để gom vào đúng bảng dimension. Quy trình gồm 2 bước:"),

      subSubHeading("6.1. Bộ từ điển phân loại (Vocabulary)"),
      bodyText("**File:** _aspect_keywords.py"),
      bodyText("Định nghĩa **8 bộ keyword** tương ứng 8 dimension, bao gồm cả tiếng Việt lẫn tiếng Anh:"),

      new Table({
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [1800, 4826, 2400],
        rows: [
          new TableRow({ children: [
            headerCell("Aspect", 1800), headerCell("Ví dụ keywords", 4826), headerCell("Unit Patterns", 2400)
          ]}),
          new TableRow({ children: [
            dataCell("**display**", 1800),
            dataCell("màn hình, độ sáng, oled, amoled, lcd, screen, resolution, refresh rate, burn-in, panel", 4826),
            dataCell("\\d+Hz (120Hz, 60Hz)", 2400)
          ]}),
          new TableRow({ children: [
            dataCell("**camera**", 1800),
            dataCell("camera, chụp, ảnh, zoom, selfie, quay, photo, lens, portrait, video", 4826),
            dataCell("\\d+MP (48MP, 64MP)", 2400)
          ]}),
          new TableRow({ children: [
            dataCell("**battery**", 1800),
            dataCell("pin, sạc, hao pin, sạc nhanh, cạn pin, battery, charge, drain, fast charge", 4826),
            dataCell("\\d+mAh, \\d+W", 2400)
          ]}),
          new TableRow({ children: [
            dataCell("**performance**", 1800),
            dataCell("hiệu năng, lag, mượt, chậm, giật, nóng máy, game, snapdragon, dimensity, cpu, gpu", 4826),
            dataCell("—", 2400)
          ]}),
          new TableRow({ children: [
            dataCell("**design**", 1800),
            dataCell("thiết kế, mỏng, nhẹ, nặng, màu sắc, vỏ máy, design, build quality, premium", 4826),
            dataCell("—", 2400)
          ]}),
          new TableRow({ children: [
            dataCell("**storage**", 1800),
            dataCell("bộ nhớ, lưu trữ, dung lượng, rom, storage, sd card, microsd", 4826),
            dataCell("\\d+GB, \\d+TB", 2400)
          ]}),
          new TableRow({ children: [
            dataCell("**connectivity**", 1800),
            dataCell("wifi, sóng, kết nối, sim, mạng, bluetooth, nfc, 5g, 4g, hotspot", 4826),
            dataCell("—", 2400)
          ]}),
          new TableRow({ children: [
            dataCell("**utilities**", 1800),
            dataCell("vân tay, chống nước, nhận diện khuôn mặt, face id, fingerprint, ip68, waterproof", 4826),
            dataCell("—", 2400)
          ]}),
        ]
      }),

      bodyText("**Kỹ thuật matching:** Regex với word boundary (\\b) + re.IGNORECASE để tránh false positive. Patterns được compile một lần khi import.", { before: 100 }),
      bodyText("**Đặc điểm:** Một comment có thể thuộc **nhiều aspect** cùng lúc (ví dụ: vừa nói camera vừa nói pin).", { italic: true }),

      subSubHeading("6.2. Bước 1 — Phân loại comment (Classification)"),
      bodyText("**Script:** run_classify_comment_aspect.py (step 1)"),
      bodyText("**Quy trình:**"),
      numberedItem("Đọc tất cả comment chưa phân loại từ dim_video_comments (WHERE aspects IS NULL AND LENGTH(TRIM(comment_text)) >= 3)", "n_embed"),
      numberedItem("Với mỗi comment, gọi hàm **keyword_match(comment_text)** — trả về dict {aspect: 1} cho mỗi aspect khớp", "n_embed"),
      numberedItem("Cập nhật cột **aspects** (kiểu JSONB) trong dim_video_comments", "n_embed"),
      numberedItem("Batch processing: fetch_size=5000, commit_every=1000 — resume-capable (bỏ qua comment đã phân loại)", "n_embed"),

      bodyText("**Ví dụ kết quả:**"),
      new Table({
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [4513, 4513],
        rows: [
          new TableRow({ children: [headerCell("comment_text", 4513), headerCell("aspects (JSONB)", 4513)] }),
          new TableRow({ children: [
            dataCell("\"Camera chụp đêm quá đẹp, pin lại trâu\"", 4513),
            dataCell("{\"camera\": 1, \"battery\": 1}", 4513)
          ]}),
          new TableRow({ children: [
            dataCell("\"Máy lag game liên quân quá\"", 4513),
            dataCell("{\"performance\": 1}", 4513)
          ]}),
          new TableRow({ children: [
            dataCell("\"Giao hàng nhanh, đóng gói cẩn thận\"", 4513),
            dataCell("{} (không thuộc aspect nào)", 4513)
          ]}),
        ]
      }),

      subSubHeading("6.3. Bước 2 — Gom comment theo aspect & sản phẩm (Aggregation)"),
      bodyText("**Script:** run_classify_comment_aspect.py (step 2)"),
      bodyText("**Quy trình:**"),
      numberedItem("Với mỗi aspect (display, camera, battery...), truy vấn tất cả comment được gắn tag aspect đó", "n_embed"),
      numberedItem("JOIN dim_video_comments → dim_video_transcripts để lấy product_id", "n_embed"),
      numberedItem("GROUP BY product_id → gom tất cả comment của cùng 1 sản phẩm, cùng 1 aspect", "n_embed"),
      numberedItem("Ghi kết quả vào cột **user_review** của bảng dimension tương ứng", "n_embed"),

      bodyText("**Mapping aspect → bảng dimension:**"),
      new Table({
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [2200, 2813, 4013],
        rows: [
          new TableRow({ children: [headerCell("Aspect", 2200), headerCell("Bảng đích", 2813), headerCell("Format user_review (JSON)", 4013)] }),
          new TableRow({ children: [dataCell("display", 2200), dataCell("dim_display", 2813), dataCell("{\"total\": N, \"comments\": [\"...\", ...]}", 4013)] }),
          new TableRow({ children: [dataCell("camera", 2200), dataCell("dim_camera", 2813), dataCell("{\"total\": N, \"comments\": [\"...\", ...]}", 4013)] }),
          new TableRow({ children: [dataCell("performance", 2200), dataCell("dim_performance", 2813), dataCell("{\"total\": N, \"comments\": [\"...\", ...]}", 4013)] }),
          new TableRow({ children: [dataCell("storage", 2200), dataCell("dim_storage", 2813), dataCell("{\"total\": N, \"comments\": [\"...\", ...]}", 4013)] }),
          new TableRow({ children: [dataCell("design", 2200), dataCell("dim_design", 2813), dataCell("{\"total\": N, \"comments\": [\"...\", ...]}", 4013)] }),
          new TableRow({ children: [dataCell("battery", 2200), dataCell("dim_battery", 2813), dataCell("{\"total\": N, \"comments\": [\"...\", ...]}", 4013)] }),
          new TableRow({ children: [dataCell("connectivity", 2200), dataCell("dim_connectivity", 2813), dataCell("{\"total\": N, \"comments\": [\"...\", ...]}", 4013)] }),
          new TableRow({ children: [dataCell("utilities", 2200), dataCell("dim_utilities", 2813), dataCell("{\"total\": N, \"comments\": [\"...\", ...]}", 4013)] }),
        ]
      }),

      bodyText("**Kết quả:** Mỗi bảng dimension giờ có cột user_review chứa tất cả bình luận thuộc aspect đó, sẵn sàng cho bước Embedding tiếp theo.", { before: 100, italic: true }),

      sectionLine(),

      // =============================================
      // SECTION 7: EMBEDDING
      // =============================================
      subHeading("7. Giai đoạn 6: Embedding & Vector Search"),

      subSubHeading("7.1. Lựa chọn Model Embedding"),
      bodyText("**Model được chọn:** dangvantuan/vietnamese-embedding (768D, XLM-RoBERTa)"),

      new Table({
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [2200, 3413, 3413],
        rows: [
          new TableRow({ children: [
            headerCell("Tiêu chí", 2200),
            headerCell("dangvantuan/vietnamese-embedding", 3413),
            headerCell("paraphrase-multilingual-MiniLM-L12-v2", 3413)
          ]}),
          new TableRow({ children: [dataCell("Chiều vector", 2200), dataCell("768D", 3413), dataCell("384D", 3413)] }),
          new TableRow({ children: [dataCell("Kiến trúc gốc", 2200), dataCell("XLM-RoBERTa", 3413), dataCell("MiniLM", 3413)] }),
          new TableRow({ children: [dataCell("Hỗ trợ tiếng Việt", 2200), dataCell("Chuyên biệt (trained on Vietnamese)", 3413), dataCell("Đa ngôn ngữ chung", 3413)] }),
          new TableRow({ children: [dataCell("Yêu cầu GPU", 2200), dataCell("Không (chạy CPU)", 3413), dataCell("Không (chạy CPU)", 3413)] }),
          new TableRow({ children: [dataCell("Chất lượng tiếng Việt", 2200), dataCell("**Cao**", 3413), dataCell("Trung bình", 3413)] }),
        ]
      }),

      bodyText("**Lý do lựa chọn:**"),
      numberedItem("**Chuyên biệt tiếng Việt** — Được huấn luyện trên dữ liệu tiếng Việt, hiểu ngữ cảnh tốt hơn mô hình đa ngôn ngữ chung", "n_reason"),
      numberedItem("**Đa ngôn ngữ** — Xử lý được bình luận YouTube bằng tiếng Việt, Anh và Indonesia", "n_reason"),
      numberedItem("**Tương thích CPU** — Không yêu cầu GPU, phù hợp triển khai production", "n_reason"),
      numberedItem("**Cân bằng chiều vector (768D)** — Đủ biểu diễn ngữ nghĩa mà không quá nặng cho pgvector", "n_reason"),

      subSubHeading("7.2. Pipeline Embedding chi tiết"),
      bodyText("**Scripts:** embedding_comment.py (3 dim đầu) + embedding_comment_remaining.py (5 dim còn lại)"),
      bodyText("**Quy trình:**"),
      numberedItem("Đọc trường **user_review** (JSON: {total, comments: [...]}) từ 8 bảng dimension trong RDS", "n_embed"),
      numberedItem("**Tokenize tiếng Việt:** pyvi.ViTokenizer.tokenize() — tách từ đúng ngữ pháp", "n_embed"),
      numberedItem("**Chia chunk:** RecursiveCharacterTextSplitter (chunk_size=160 tokens, overlap=20 tokens)", "n_embed"),
      numberedItem("**Giới hạn token:** MAX_TOKENS=254 (do buffer issue của XLM-RoBERTa)", "n_embed"),
      numberedItem("**Encode:** SentenceTransformer với normalize_embeddings=True → vector 768 chiều", "n_embed"),
      numberedItem("**Lưu vào RDS:** Bảng comment_embeddings với pgvector (ON CONFLICT DO NOTHING)", "n_embed"),

      bodyText("**Bảng comment_embeddings:**"),
      new Table({
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [2200, 2213, 4613],
        rows: [
          new TableRow({ children: [headerCell("Cột", 2200), headerCell("Kiểu", 2213), headerCell("Mô tả", 4613)] }),
          new TableRow({ children: [dataCell("chunk_id", 2200), dataCell("SERIAL PK", 2213), dataCell("ID tự động tăng", 4613)] }),
          new TableRow({ children: [dataCell("dim_id", 2200), dataCell("INTEGER", 2213), dataCell("ID của bản ghi trong bảng dimension nguồn", 4613)] }),
          new TableRow({ children: [dataCell("dim_table", 2200), dataCell("VARCHAR(30)", 2213), dataCell("Tên bảng dimension nguồn (dim_display, dim_camera, ...)", 4613)] }),
          new TableRow({ children: [dataCell("list_index", 2200), dataCell("INTEGER", 2213), dataCell("Vị trí comment trong danh sách", 4613)] }),
          new TableRow({ children: [dataCell("chunk_index", 2200), dataCell("INTEGER", 2213), dataCell("Vị trí chunk trong comment", 4613)] }),
          new TableRow({ children: [dataCell("chunk_text", 2200), dataCell("TEXT", 2213), dataCell("Nội dung text của chunk", 4613)] }),
          new TableRow({ children: [dataCell("embedding", 2200), dataCell("vector(768)", 2213), dataCell("Vector embedding 768 chiều (pgvector)", 4613)] }),
          new TableRow({ children: [dataCell("created_at", 2200), dataCell("TIMESTAMP", 2213), dataCell("Thời gian tạo", 4613)] }),
        ]
      }),

      bodyText("**Index:** IVFFlat với vector_cosine_ops cho tìm kiếm tương đồng nhanh"),
      bodyText("**Batch processing:** batch_size mặc định 512, idempotent (ON CONFLICT DO NOTHING)"),

      sectionLine(),

      // =============================================
      // SECTION 7: TỔNG KẾT LUỒNG
      // =============================================
      subHeading("8. Tổng kết luồng dữ liệu end-to-end"),

      new Table({
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [500, 2000, 3026, 3500],
        rows: [
          new TableRow({ children: [
            colorHeaderCell("#", 500, LIGHT_GREEN), colorHeaderCell("Bước", 2000, LIGHT_GREEN),
            colorHeaderCell("Script", 3026, LIGHT_GREEN), colorHeaderCell("Đầu ra", 3500, LIGHT_GREEN)
          ]}),
          new TableRow({ children: [
            dataCell("1", 500), dataCell("Cào links", 2000),
            dataCell("run_crawl_product_links.py", 3026), dataCell("data/raw/product_links.json", 3500)
          ]}),
          new TableRow({ children: [
            dataCell("2", 500), dataCell("Cào specs", 2000),
            dataCell("run_crawl_all_specs.py", 3026), dataCell("data/raw/all_product_specs_raw.json", 3500)
          ]}),
          new TableRow({ children: [
            dataCell("3", 500), dataCell("Dedup (MD5)", 2000),
            dataCell("run_deduplicate_specs.py", 3026), dataCell("data/processed/unique_smartphone_specs.json + suspected_duplicates.json", 3500)
          ]}),
          new TableRow({ children: [
            dataCell("4", 500), dataCell("LLM normalize", 2000),
            dataCell("run_llm_name_normalization.py", 3026), dataCell("data/processed/ready_to_load_specs.json", 3500)
          ]}),
          new TableRow({ children: [
            dataCell("5", 500), dataCell("Final dedup", 2000),
            dataCell("run_final_deduplication.py", 3026), dataCell("data/processed/final_ready_to_load_specs.json", 3500)
          ]}),
          new TableRow({ children: [
            dataCell("6", 500), dataCell("Bootstrap DB", 2000),
            dataCell("bootstrap_db.py", 3026), dataCell("Tạo schema: fact + 8 dims + video tables", 3500)
          ]}),
          new TableRow({ children: [
            dataCell("7", 500), dataCell("Load to RDS", 2000),
            dataCell("load_products_to_db.py", 3026), dataCell("RDS: fact_product + 8 dim_* tables", 3500)
          ]}),
          new TableRow({ children: [
            dataCell("8", 500), dataCell("YouTube media", 2000),
            dataCell("run_unique_smartphone_media_flow.py", 3026), dataCell("Local temp → S3 → RDS (dim_video_*)", 3500)
          ]}),
          new TableRow({ children: [
            dataCell("9", 500, { fill: LIGHT_YELLOW }), dataCell("**Classify comments**", 2000, { fill: LIGHT_YELLOW }),
            dataCell("run_classify_comment_aspect.py", 3026, { fill: LIGHT_YELLOW }), dataCell("dim_video_comments.aspects (JSONB) → dim_*.user_review (JSON)", 3500, { fill: LIGHT_YELLOW })
          ]}),
          new TableRow({ children: [
            dataCell("10", 500), dataCell("Embedding", 2000),
            dataCell("embedding_comment.py + _remaining.py", 3026), dataCell("RDS: comment_embeddings (pgvector 768D)", 3500)
          ]}),
        ]
      }),

      sectionLine(),

      // ===== PAGE BREAK + STAGE 2 =====
      new Paragraph({ children: [new PageBreak()] }),
      stageHeading("STAGE 2: XÂY DỰNG HỆ THỐNG AGENTIC AI"),
      new Paragraph({ spacing: { before: 200 }, children: [] }),
      bodyText("(Phần này sẽ được bổ sung sau)", { italic: true, align: AlignmentType.CENTER }),
    ]
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("E:\\DS200_Do_an\\DS200_Big_Data\\Stage1_Summary_Report.docx", buffer);
  console.log("OK: Stage1_Summary_Report.docx created");
});
