CREATE TABLE fact_product (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL, -- Tên điện thoại
    os_version VARCHAR(100),            -- Hệ điều hành
    language_support VARCHAR(255),      -- Ngôn ngữ
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Màn hình
CREATE TABLE dim_display (
    dim_id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES fact_product(product_id),
    
    -- Các thuộc tính
    display_type VARCHAR(100),       -- Loại màn hình: Super AMOLED
    color_depth VARCHAR(50),         -- Màu màn hình: 16 triệu màu
    display_standard TEXT,           -- Chuẩn màn hình (Lưu text tổng quát nếu cần)
    resolution VARCHAR(100),         -- Độ phân giải: 1080 x 2340 pixels
    screen_size VARCHAR(50),         -- Màn hình rộng: 6.7 inches
    touch_technology VARCHAR(255),   -- Công nghệ cảm ứng: Cảm ứng điện dung đa điểm
    
    -- 2 cột bắt buộc cho bài toán Sentiment
    youtuber_review TEXT,            -- Tóm tắt cảm nhận từ các Reviewer
    user_review TEXT,                -- Tóm tắt ý kiến từ thảo luận người dùng
    
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Camera
CREATE TABLE dim_camera (
    dim_id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES fact_product(product_id),
    
    -- Các thuộc tính nguyên bản từ ảnh chuyển sang Tiếng Anh
    rear_camera TEXT,           -- Camera sau
    front_camera TEXT,          -- Camera trước
    flash_light VARCHAR(50),    -- Đèn Flash
    camera_features TEXT,       -- Tính năng camera
    video_recording TEXT,       -- Quay phim
    video_call VARCHAR(50),     -- Videocall
    
    -- 2 cột bắt buộc cho bài toán Sentiment
    youtuber_review TEXT,
    user_review TEXT,
    
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Hiệu năng
CREATE TABLE dim_performance (
    dim_id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES fact_product(product_id),
    cpu_speed TEXT,             -- Tốc độ CPU
    core_count VARCHAR(100),    -- Số nhân
    chipset TEXT,               -- Chipset
    ram_capacity VARCHAR(100),  -- RAM
    gpu_chip VARCHAR(255),      -- Chip đồ họa (GPU)
    youtuber_review TEXT,
    user_review TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bộ nhớ và lưu trữ
CREATE TABLE dim_storage (
    dim_id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES fact_product(product_id),
    phonebook_storage VARCHAR(255), -- Danh bạ
    internal_storage TEXT,          -- Bộ nhớ trong (ROM)
    external_memory VARCHAR(255),   -- Thẻ nhớ ngoài
    max_external_support VARCHAR(255), -- Hỗ trợ thẻ tối đa
    youtuber_review TEXT,
    user_review TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Thiết kế & Trọng lượng
CREATE TABLE dim_design (
    dim_id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES fact_product(product_id),
    design_style TEXT,          -- Kiểu dáng
    dimensions VARCHAR(255),    -- Kích thước
    weight VARCHAR(100),        -- Trọng lượng (g)
    youtuber_review TEXT,
    user_review TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Pin
CREATE TABLE dim_battery (
    dim_id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES fact_product(product_id),
    battery_type VARCHAR(255),      -- Loại pin
    battery_capacity TEXT,          -- Dung lượng pin (bao gồm cả sạc nhanh)
    removable_battery VARCHAR(50),  -- Pin có thể tháo rời
    youtuber_review TEXT,
    user_review TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Kết nối và cổng giao tiếp
CREATE TABLE dim_connectivity (
    dim_id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES fact_product(product_id),
    
    network_3g TEXT,                -- 3G
    network_4g TEXT,                -- 4G
    sim_type VARCHAR(255),          -- Loại Sim
    sim_slots VARCHAR(255),         -- Khe gắn Sim
    wifi TEXT,                      -- Wifi
    gps TEXT,                       -- GPS
    bluetooth VARCHAR(255),         -- Bluetooth
    gprs_edge VARCHAR(50),          -- GPRS/EDGE
    headphone_jack VARCHAR(255),    -- Jack tai nghe
    nfc VARCHAR(50),                -- NFC
    usb_connection VARCHAR(255),    -- Kết nối USB
    other_connections TEXT,         -- Kết nối khác
    charging_port VARCHAR(100),     -- Cổng sạc
    
    youtuber_review TEXT,
    user_review TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

--Giải trí & Ứng dụng.
CREATE TABLE dim_utilities (
    dim_id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES fact_product(product_id),
    
    movie_playback TEXT,            -- Xem phim
    music_playback TEXT,            -- Nghe nhạc
    charging_port_alt VARCHAR(100), -- Cổng sạc (mục con của giải trí)
    voice_recorder VARCHAR(50),     -- Ghi âm
    fm_radio VARCHAR(50),           -- FM radio
    other_features TEXT,            -- Chức năng khác
    
    youtuber_review TEXT,
    user_review TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


