-- Jaffle Shop Demo Database
-- Extended from dbt jaffle_shop with realistic e-commerce data
-- Includes data quality issues and PII for testing OpenMetadata features

-- Create Metabase database
CREATE DATABASE metabase;

-- =============================================================================
-- SCHEMAS
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS raw_jaffle_shop;
CREATE SCHEMA IF NOT EXISTS raw_stripe;
CREATE SCHEMA IF NOT EXISTS raw_marketing;
CREATE SCHEMA IF NOT EXISTS raw_inventory;
CREATE SCHEMA IF NOT EXISTS raw_support;
CREATE SCHEMA IF NOT EXISTS analytics;

-- dbt-managed schemas (pre-created so permissions can be granted upfront)
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS intermediate;
CREATE SCHEMA IF NOT EXISTS marts_core;
CREATE SCHEMA IF NOT EXISTS marts_finance;
CREATE SCHEMA IF NOT EXISTS marts_marketing;

-- =============================================================================
-- RAW_JAFFLE_SHOP: Core customer and order data
-- =============================================================================

-- Customers table with PII
CREATE TABLE raw_jaffle_shop.customers (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100),
    phone_number VARCHAR(20),
    date_of_birth DATE,
    ssn_last_four VARCHAR(4),
    address_line_1 VARCHAR(200),
    city VARCHAR(100),
    state VARCHAR(50),
    postal_code VARCHAR(20),
    country VARCHAR(50) DEFAULT 'USA',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE raw_jaffle_shop.customers IS 'Raw customer data from the Jaffle Shop application. Contains PII that requires masking.';
COMMENT ON COLUMN raw_jaffle_shop.customers.email IS 'Customer email address - PII';
COMMENT ON COLUMN raw_jaffle_shop.customers.ssn_last_four IS 'Last 4 digits of SSN - Sensitive PII';

-- Orders table
CREATE TABLE raw_jaffle_shop.orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES raw_jaffle_shop.customers(id),
    order_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL,
    order_total DECIMAL(10, 2),
    shipping_cost DECIMAL(10, 2),
    discount_amount DECIMAL(10, 2) DEFAULT 0,
    coupon_code VARCHAR(20),
    shipping_address_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE raw_jaffle_shop.orders IS 'Raw orders from the Jaffle Shop e-commerce platform';

-- Order items (line items)
CREATE TABLE raw_jaffle_shop.order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES raw_jaffle_shop.orders(id),
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- =============================================================================
-- RAW_STRIPE: Payment processing data
-- =============================================================================

CREATE TABLE raw_stripe.payments (
    id SERIAL PRIMARY KEY,
    order_id INTEGER,
    payment_method VARCHAR(20) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    card_last_four VARCHAR(4),
    card_brand VARCHAR(20),
    billing_email VARCHAR(100),
    ip_address INET,
    risk_score INTEGER
);

COMMENT ON TABLE raw_stripe.payments IS 'Payment transactions from Stripe. Contains card info and IP addresses.';
COMMENT ON COLUMN raw_stripe.payments.card_last_four IS 'Last 4 digits of payment card - PCI data';
COMMENT ON COLUMN raw_stripe.payments.ip_address IS 'Customer IP address at time of payment';

-- Refunds
CREATE TABLE raw_stripe.refunds (
    id SERIAL PRIMARY KEY,
    payment_id INTEGER REFERENCES raw_stripe.payments(id),
    amount DECIMAL(10, 2) NOT NULL,
    reason VARCHAR(100),
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL
);

-- =============================================================================
-- RAW_INVENTORY: Product and inventory data
-- =============================================================================

CREATE TABLE raw_inventory.products (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(50),
    subcategory VARCHAR(50),
    unit_cost DECIMAL(10, 2) NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    weight_kg DECIMAL(5, 2),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE raw_inventory.suppliers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    contact_name VARCHAR(100),
    contact_email VARCHAR(100),
    phone VARCHAR(20),
    address TEXT,
    country VARCHAR(50),
    lead_time_days INTEGER,
    rating DECIMAL(2, 1),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE raw_inventory.stock_levels (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES raw_inventory.products(id),
    warehouse_location VARCHAR(50) NOT NULL,
    quantity_on_hand INTEGER NOT NULL DEFAULT 0,
    quantity_reserved INTEGER NOT NULL DEFAULT 0,
    reorder_point INTEGER NOT NULL DEFAULT 10,
    last_restocked_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- =============================================================================
-- RAW_MARKETING: Campaign and web analytics data
-- =============================================================================

CREATE TABLE raw_marketing.campaigns (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    channel VARCHAR(50) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    budget DECIMAL(12, 2),
    target_audience VARCHAR(100),
    status VARCHAR(20) DEFAULT 'active',
    created_by VARCHAR(100)
);

CREATE TABLE raw_marketing.ad_spend (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER REFERENCES raw_marketing.campaigns(id),
    spend_date DATE NOT NULL,
    impressions INTEGER,
    clicks INTEGER,
    conversions INTEGER,
    spend_amount DECIMAL(10, 2) NOT NULL,
    platform VARCHAR(50)
);

CREATE TABLE raw_marketing.user_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    customer_id INTEGER,
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    page_views INTEGER DEFAULT 0,
    utm_source VARCHAR(50),
    utm_medium VARCHAR(50),
    utm_campaign VARCHAR(100),
    device_type VARCHAR(20),
    browser VARCHAR(50),
    ip_address INET,
    country VARCHAR(50),
    region VARCHAR(50)
);

CREATE TABLE raw_marketing.events (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    event_timestamp TIMESTAMP NOT NULL,
    page_url TEXT,
    product_id INTEGER,
    event_properties JSONB
);

-- =============================================================================
-- RAW_SUPPORT: Customer service data
-- =============================================================================

CREATE TABLE raw_support.tickets (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER,
    order_id INTEGER,
    subject VARCHAR(200) NOT NULL,
    description TEXT,
    priority VARCHAR(20) DEFAULT 'medium',
    status VARCHAR(20) DEFAULT 'open',
    category VARCHAR(50),
    assigned_to VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    satisfaction_score INTEGER CHECK (satisfaction_score BETWEEN 1 AND 5)
);

CREATE TABLE raw_support.reviews (
    id SERIAL PRIMARY KEY,
    product_id INTEGER,
    customer_id INTEGER,
    order_id INTEGER,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    title VARCHAR(200),
    review_text TEXT,
    is_verified_purchase BOOLEAN DEFAULT FALSE,
    helpful_votes INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- =============================================================================
-- SEED DATA: Customers
-- =============================================================================

INSERT INTO raw_jaffle_shop.customers (first_name, last_name, email, phone_number, date_of_birth, ssn_last_four, address_line_1, city, state, postal_code, created_at) VALUES
('Michael', 'Perez', 'mperez@example.com', '555-0101', '1985-03-15', '1234', '123 Main St', 'Austin', 'TX', '78701', '2023-01-05'),
('Shawn', 'Myers', 'smyers@example.com', '555-0102', '1990-07-22', '5678', '456 Oak Ave', 'Seattle', 'WA', '98101', '2023-01-12'),
('Kathleen', 'Johnson', 'kjohnson@example.com', '555-0103', '1988-11-30', '9012', '789 Pine Rd', 'Denver', 'CO', '80201', '2023-02-01'),
('Jimmy', 'Ramirez', 'jramirez@example.com', '555-0104', '1992-05-18', '3456', '321 Elm St', 'Portland', 'OR', '97201', '2023-02-15'),
('Sara', 'Chen', 'schen@example.com', '555-0105', '1987-09-08', '7890', '654 Maple Dr', 'San Francisco', 'CA', '94102', '2023-03-01'),
('Diana', 'Williams', 'dwilliams@example.com', '555-0106', '1995-01-25', '2345', '987 Cedar Ln', 'Chicago', 'IL', '60601', '2023-03-10'),
('Martin', 'Garcia', 'mgarcia@example.com', '555-0107', '1983-12-12', '6789', '147 Birch Blvd', 'Miami', 'FL', '33101', '2023-03-22'),
('Jennifer', 'Davis', 'jdavis@example.com', '555-0108', '1991-06-05', '0123', '258 Willow Way', 'Boston', 'MA', '02101', '2023-04-05'),
('Richard', 'Anderson', 'randerson@example.com', '555-0109', '1986-04-17', '4567', '369 Spruce St', 'Phoenix', 'AZ', '85001', '2023-04-18'),
('Amanda', 'Taylor', 'ataylor@example.com', '555-0110', '1993-08-29', '8901', '741 Ash Ave', 'Dallas', 'TX', '75201', '2023-05-01'),
-- Customers with data quality issues (for DQ demos)
('John', 'Smith', NULL, NULL, '1980-01-01', NULL, '100 Test St', 'New York', 'NY', '10001', '2023-05-15'), -- Missing email
('', 'Unknown', 'unknown@test.com', '555-0112', NULL, NULL, '', '', '', '', '2023-05-20'), -- Empty strings
('Test', 'User', 'invalid-email', '555-0113', '2050-01-01', '0000', '123 Future St', 'Nowhere', 'XX', '00000', '2023-06-01'), -- Invalid data
('Duplicate', 'Customer', 'duplicate@example.com', '555-0114', '1990-01-01', '1111', '111 Same St', 'Austin', 'TX', '78701', '2023-06-10'),
('Duplicate', 'Customer', 'duplicate@example.com', '555-0114', '1990-01-01', '1111', '111 Same St', 'Austin', 'TX', '78701', '2023-06-10'), -- Intentional duplicate
-- More regular customers
('Emily', 'Brown', 'ebrown@example.com', '555-0115', '1994-02-14', '2222', '222 Love Ln', 'Las Vegas', 'NV', '89101', '2023-06-15'),
('David', 'Miller', 'dmiller@example.com', '555-0116', '1989-10-31', '3333', '333 Spooky Rd', 'Salem', 'MA', '01970', '2023-07-01'),
('Jessica', 'Wilson', 'jwilson@example.com', '555-0117', '1996-07-04', '4444', '444 Freedom Ave', 'Philadelphia', 'PA', '19101', '2023-07-15'),
('Christopher', 'Moore', 'cmoore@example.com', '555-0118', '1984-03-17', '5555', '555 Lucky St', 'Dublin', 'OH', '43017', '2023-08-01'),
('Ashley', 'Thomas', 'athomas@example.com', '555-0119', '1997-12-25', '6666', '666 Holiday Ct', 'Santa Claus', 'IN', '47579', '2023-08-15'),
('Matthew', 'Jackson', 'mjackson@example.com', '555-0120', '1982-09-15', '7777', '777 Music Row', 'Nashville', 'TN', '37201', '2023-09-01'),
('Stephanie', 'White', 'swhite@example.com', '555-0121', '1998-04-22', '8888', '888 Clean St', 'Salt Lake City', 'UT', '84101', '2023-09-15'),
('Andrew', 'Harris', 'aharris@example.com', '555-0122', '1981-11-11', '9999', '999 Veteran Way', 'Arlington', 'VA', '22201', '2023-10-01'),
('Nicole', 'Martin', 'nmartin@example.com', '555-0123', '1999-06-21', '1010', '1010 Binary Blvd', 'San Jose', 'CA', '95101', '2023-10-15'),
('Joshua', 'Thompson', 'jthompson@example.com', '555-0124', '1985-08-08', '2020', '2020 Vision Dr', 'Atlanta', 'GA', '30301', '2023-11-01');

-- =============================================================================
-- SEED DATA: Products
-- =============================================================================

INSERT INTO raw_inventory.products (sku, name, description, category, subcategory, unit_cost, unit_price, weight_kg, is_active) VALUES
('JFL-001', 'Classic Jaffle', 'Traditional toasted sandwich with cheese', 'Food', 'Jaffles', 2.50, 8.99, 0.25, TRUE),
('JFL-002', 'Veggie Supreme Jaffle', 'Loaded with fresh vegetables and cheese', 'Food', 'Jaffles', 3.00, 10.99, 0.30, TRUE),
('JFL-003', 'Meat Lovers Jaffle', 'Ham, bacon, and cheese jaffle', 'Food', 'Jaffles', 3.50, 12.99, 0.35, TRUE),
('JFL-004', 'Spicy Chicken Jaffle', 'Cajun chicken with pepper jack', 'Food', 'Jaffles', 3.25, 11.99, 0.30, TRUE),
('JFL-005', 'Breakfast Jaffle', 'Egg, bacon, and cheese morning treat', 'Food', 'Jaffles', 3.00, 10.99, 0.28, TRUE),
('BEV-001', 'Fresh Lemonade', 'House-made lemonade', 'Beverage', 'Cold Drinks', 0.75, 3.99, 0.40, TRUE),
('BEV-002', 'Iced Coffee', 'Cold brew coffee over ice', 'Beverage', 'Cold Drinks', 1.00, 4.99, 0.45, TRUE),
('BEV-003', 'Hot Coffee', 'Premium roast coffee', 'Beverage', 'Hot Drinks', 0.50, 2.99, 0.35, TRUE),
('BEV-004', 'Chai Latte', 'Spiced chai with steamed milk', 'Beverage', 'Hot Drinks', 1.25, 5.49, 0.40, TRUE),
('BEV-005', 'Green Smoothie', 'Spinach, banana, and apple', 'Beverage', 'Smoothies', 2.00, 6.99, 0.50, TRUE),
('SDE-001', 'Sweet Potato Fries', 'Crispy seasoned sweet potato fries', 'Food', 'Sides', 1.50, 4.99, 0.20, TRUE),
('SDE-002', 'Garden Salad', 'Mixed greens with house dressing', 'Food', 'Sides', 1.25, 5.99, 0.25, TRUE),
('SDE-003', 'Soup of the Day', 'Chef''s daily soup selection', 'Food', 'Sides', 1.75, 5.49, 0.35, TRUE),
('DST-001', 'Chocolate Brownie', 'Rich fudge brownie', 'Food', 'Desserts', 1.00, 4.49, 0.15, TRUE),
('DST-002', 'Apple Pie Jaffle', 'Sweet apple cinnamon dessert jaffle', 'Food', 'Desserts', 2.00, 7.99, 0.25, TRUE),
('MRC-001', 'Jaffle Shop T-Shirt', 'Cotton branded t-shirt', 'Merchandise', 'Apparel', 8.00, 24.99, 0.20, TRUE),
('MRC-002', 'Coffee Mug', 'Ceramic mug with logo', 'Merchandise', 'Accessories', 4.00, 14.99, 0.35, TRUE),
('MRC-003', 'Tote Bag', 'Reusable canvas tote', 'Merchandise', 'Accessories', 3.00, 12.99, 0.15, TRUE),
-- Discontinued products
('JFL-OLD', 'Discontinued Jaffle', 'No longer available', 'Food', 'Jaffles', 2.00, 7.99, 0.25, FALSE),
('BEV-OLD', 'Discontinued Drink', 'Removed from menu', 'Beverage', 'Cold Drinks', 1.00, 3.99, 0.40, FALSE);

-- =============================================================================
-- SEED DATA: Suppliers
-- =============================================================================

INSERT INTO raw_inventory.suppliers (name, contact_name, contact_email, phone, address, country, lead_time_days, rating, is_active) VALUES
('Fresh Farms Co', 'Bob Farmer', 'bob@freshfarms.com', '555-1001', '100 Farm Road, Sacramento, CA', 'USA', 3, 4.5, TRUE),
('Bakery Wholesale', 'Alice Baker', 'alice@bakerywholesale.com', '555-1002', '200 Bread St, San Francisco, CA', 'USA', 2, 4.8, TRUE),
('Beverage Distributors Inc', 'Charlie Drinks', 'charlie@bevdist.com', '555-1003', '300 Bottle Ave, Oakland, CA', 'USA', 5, 4.2, TRUE),
('Quality Meats LLC', 'Diana Butcher', 'diana@qualitymeats.com', '555-1004', '400 Meat Market, Fresno, CA', 'USA', 2, 4.7, TRUE),
('Pacific Coffee Roasters', 'Edward Roast', 'edward@pacificcoffee.com', '555-1005', '500 Bean Blvd, Portland, OR', 'USA', 7, 4.9, TRUE),
('Merchandise Plus', 'Fiona Merch', 'fiona@merchplus.com', '555-1006', '600 Print St, Los Angeles, CA', 'USA', 14, 4.0, TRUE);

-- =============================================================================
-- SEED DATA: Stock Levels
-- =============================================================================

INSERT INTO raw_inventory.stock_levels (product_id, warehouse_location, quantity_on_hand, quantity_reserved, reorder_point, last_restocked_at) VALUES
(1, 'MAIN', 150, 20, 50, '2024-01-15'),
(2, 'MAIN', 100, 15, 40, '2024-01-15'),
(3, 'MAIN', 80, 10, 30, '2024-01-14'),
(4, 'MAIN', 90, 12, 35, '2024-01-14'),
(5, 'MAIN', 120, 18, 45, '2024-01-15'),
(6, 'MAIN', 200, 30, 75, '2024-01-13'),
(7, 'MAIN', 180, 25, 60, '2024-01-13'),
(8, 'MAIN', 250, 40, 100, '2024-01-12'),
(9, 'MAIN', 150, 20, 50, '2024-01-14'),
(10, 'MAIN', 80, 10, 30, '2024-01-15'),
(11, 'MAIN', 100, 15, 40, '2024-01-14'),
(12, 'MAIN', 90, 12, 35, '2024-01-15'),
(13, 'MAIN', 60, 8, 25, '2024-01-14'),
(14, 'MAIN', 70, 10, 30, '2024-01-15'),
(15, 'MAIN', 50, 5, 20, '2024-01-13'),
(16, 'MAIN', 30, 5, 15, '2024-01-10'),
(17, 'MAIN', 45, 8, 20, '2024-01-10'),
(18, 'MAIN', 40, 6, 15, '2024-01-10'),
-- Low stock items (for alerts)
(1, 'EAST', 5, 3, 50, '2024-01-01'), -- Below reorder point
(3, 'EAST', 8, 5, 30, '2024-01-05'); -- Below reorder point

-- =============================================================================
-- SEED DATA: Orders (realistic patterns over time)
-- =============================================================================

INSERT INTO raw_jaffle_shop.orders (customer_id, order_date, status, order_total, shipping_cost, discount_amount, coupon_code, created_at) VALUES
-- January 2024 orders
(1, '2024-01-02', 'completed', 23.97, 0, 0, NULL, '2024-01-02 10:15:00'),
(2, '2024-01-03', 'completed', 15.98, 0, 0, NULL, '2024-01-03 12:30:00'),
(3, '2024-01-05', 'completed', 34.96, 0, 3.50, 'WELCOME10', '2024-01-05 14:45:00'),
(1, '2024-01-08', 'completed', 18.97, 0, 0, NULL, '2024-01-08 09:20:00'),
(4, '2024-01-10', 'completed', 42.95, 5.99, 0, NULL, '2024-01-10 16:00:00'),
(5, '2024-01-12', 'completed', 27.97, 0, 2.80, 'SAVE10', '2024-01-12 11:30:00'),
(6, '2024-01-15', 'completed', 19.98, 0, 0, NULL, '2024-01-15 13:15:00'),
(7, '2024-01-17', 'completed', 55.94, 5.99, 5.59, 'LOYALTY10', '2024-01-17 15:45:00'),
(2, '2024-01-19', 'completed', 12.99, 0, 0, NULL, '2024-01-19 10:00:00'),
(8, '2024-01-22', 'completed', 31.97, 0, 0, NULL, '2024-01-22 12:20:00'),
(9, '2024-01-24', 'completed', 24.98, 0, 0, NULL, '2024-01-24 14:10:00'),
(10, '2024-01-26', 'completed', 39.96, 0, 4.00, 'FLASH10', '2024-01-26 16:30:00'),
(3, '2024-01-28', 'completed', 21.98, 0, 0, NULL, '2024-01-28 09:45:00'),
(5, '2024-01-30', 'completed', 28.97, 0, 0, NULL, '2024-01-30 11:15:00'),
-- February orders (slightly higher volume)
(1, '2024-02-01', 'completed', 33.96, 0, 0, NULL, '2024-02-01 10:30:00'),
(4, '2024-02-02', 'completed', 45.95, 5.99, 4.60, 'FEB10', '2024-02-02 12:00:00'),
(6, '2024-02-03', 'completed', 22.98, 0, 0, NULL, '2024-02-03 14:15:00'),
(11, '2024-02-05', 'completed', 17.98, 0, 0, NULL, '2024-02-05 09:00:00'),
(12, '2024-02-06', 'completed', 29.97, 0, 0, NULL, '2024-02-06 11:30:00'),
(7, '2024-02-08', 'completed', 38.96, 0, 3.90, 'SAVE10', '2024-02-08 13:45:00'),
(13, '2024-02-10', 'completed', 51.94, 5.99, 0, NULL, '2024-02-10 15:00:00'),
(8, '2024-02-12', 'completed', 26.98, 0, 0, NULL, '2024-02-12 10:20:00'),
(14, '2024-02-14', 'completed', 62.93, 0, 6.29, 'VALENTINE', '2024-02-14 12:00:00'), -- Valentine's Day
(15, '2024-02-14', 'completed', 44.96, 0, 4.50, 'VALENTINE', '2024-02-14 14:30:00'),
(9, '2024-02-16', 'completed', 19.98, 0, 0, NULL, '2024-02-16 16:00:00'),
(2, '2024-02-18', 'completed', 35.96, 0, 0, NULL, '2024-02-18 09:30:00'),
(10, '2024-02-20', 'completed', 28.97, 0, 0, NULL, '2024-02-20 11:45:00'),
(16, '2024-02-22', 'completed', 23.98, 0, 0, NULL, '2024-02-22 13:15:00'),
(17, '2024-02-24', 'completed', 41.95, 5.99, 0, NULL, '2024-02-24 15:30:00'),
(1, '2024-02-26', 'completed', 30.97, 0, 3.10, 'THANKS10', '2024-02-26 10:00:00'),
(18, '2024-02-28', 'completed', 37.96, 0, 0, NULL, '2024-02-28 12:30:00'),
-- March orders (continued growth)
(3, '2024-03-01', 'completed', 25.98, 0, 0, NULL, '2024-03-01 14:00:00'),
(19, '2024-03-02', 'completed', 48.95, 5.99, 4.90, 'MARCH10', '2024-03-02 09:15:00'),
(5, '2024-03-04', 'completed', 21.98, 0, 0, NULL, '2024-03-04 11:30:00'),
(20, '2024-03-05', 'completed', 33.97, 0, 0, NULL, '2024-03-05 13:45:00'),
(21, '2024-03-07', 'completed', 56.94, 5.99, 5.69, 'LOYALTY10', '2024-03-07 15:00:00'),
(6, '2024-03-09', 'completed', 18.98, 0, 0, NULL, '2024-03-09 10:30:00'),
(22, '2024-03-11', 'completed', 42.96, 0, 0, NULL, '2024-03-11 12:00:00'),
(7, '2024-03-13', 'completed', 29.97, 0, 3.00, 'SAVE10', '2024-03-13 14:15:00'),
(23, '2024-03-15', 'completed', 64.93, 5.99, 6.49, 'SPRING10', '2024-03-15 09:45:00'),
(8, '2024-03-17', 'completed', 35.96, 0, 0, NULL, '2024-03-17 11:00:00'),
(24, '2024-03-19', 'completed', 27.98, 0, 0, NULL, '2024-03-19 13:30:00'),
(9, '2024-03-21', 'completed', 44.95, 5.99, 0, NULL, '2024-03-21 15:45:00'),
(25, '2024-03-23', 'completed', 31.97, 0, 0, NULL, '2024-03-23 10:00:00'),
(10, '2024-03-25', 'completed', 23.98, 0, 2.40, 'FLASH10', '2024-03-25 12:15:00'),
(1, '2024-03-27', 'completed', 52.94, 0, 5.29, 'VIP10', '2024-03-27 14:30:00'),
(2, '2024-03-29', 'completed', 38.96, 0, 0, NULL, '2024-03-29 09:00:00'),
(3, '2024-03-31', 'completed', 26.98, 0, 0, NULL, '2024-03-31 11:30:00'),
-- Orders with issues (for DQ demos)
(11, '2024-04-01', 'completed', NULL, 0, 0, NULL, '2024-04-01 10:00:00'), -- Missing total
(NULL, '2024-04-02', 'pending', 25.98, 0, 0, NULL, '2024-04-02 12:00:00'), -- Missing customer (orphan)
(12, '2024-04-03', 'cancelled', 0, 0, 0, NULL, '2024-04-03 14:00:00'), -- Zero total cancelled
(13, '2024-04-04', 'return_pending', 45.95, 5.99, 0, NULL, '2024-04-04 16:00:00'),
(14, '2024-04-05', 'shipped', 32.97, 0, 0, NULL, '2024-04-05 09:30:00'),
(15, '2024-04-06', 'processing', 28.98, 0, 2.90, 'APRIL10', '2024-04-06 11:45:00'),
-- Recent orders
(16, '2024-04-08', 'completed', 41.96, 0, 0, NULL, '2024-04-08 13:00:00'),
(17, '2024-04-10', 'completed', 55.94, 5.99, 5.59, 'SPRING10', '2024-04-10 15:15:00'),
(18, '2024-04-12', 'completed', 23.98, 0, 0, NULL, '2024-04-12 10:30:00'),
(19, '2024-04-14', 'completed', 37.96, 0, 0, NULL, '2024-04-14 12:45:00'),
(20, '2024-04-16', 'shipped', 48.95, 5.99, 4.90, 'LOYAL10', '2024-04-16 14:00:00');

-- =============================================================================
-- SEED DATA: Order Items
-- =============================================================================

INSERT INTO raw_jaffle_shop.order_items (order_id, product_id, quantity, unit_price) VALUES
-- Order 1: Classic combo
(1, 1, 2, 8.99), (1, 6, 1, 3.99),
-- Order 2: Coffee lover
(2, 8, 2, 2.99), (2, 14, 1, 4.49), (2, 11, 1, 4.99),
-- Order 3: Lunch special
(3, 2, 1, 10.99), (3, 3, 1, 12.99), (3, 7, 2, 4.99),
-- Order 4: Quick bite
(4, 1, 1, 8.99), (4, 8, 1, 2.99), (4, 14, 1, 4.49),
-- Order 5: Family order
(5, 1, 2, 8.99), (5, 2, 1, 10.99), (5, 3, 1, 12.99), (5, 6, 2, 3.99),
-- Order 6: Healthy choice
(6, 2, 1, 10.99), (6, 10, 1, 6.99), (6, 12, 1, 5.99),
-- Order 7: Simple order
(7, 4, 1, 11.99), (7, 9, 1, 5.49),
-- Order 8: Big spender with merch
(8, 1, 2, 8.99), (8, 5, 1, 10.99), (8, 16, 1, 24.99),
-- Order 9: Just dessert
(9, 15, 1, 7.99), (9, 9, 1, 4.99),
-- Order 10: Lunch group
(10, 1, 1, 8.99), (10, 2, 1, 10.99), (10, 3, 1, 12.99),
-- Continue pattern for remaining orders
(11, 4, 2, 11.99), (12, 5, 1, 10.99), (12, 7, 2, 4.99), (12, 11, 1, 4.99),
(13, 1, 1, 8.99), (13, 8, 2, 2.99), (13, 12, 1, 5.99),
(14, 2, 2, 10.99), (14, 6, 2, 3.99),
(15, 3, 1, 12.99), (15, 4, 1, 11.99), (15, 8, 3, 2.99),
(16, 1, 3, 8.99), (16, 14, 2, 4.49),
(17, 5, 2, 10.99), (17, 10, 1, 6.99), (17, 17, 1, 14.99),
(18, 2, 1, 10.99), (18, 11, 2, 4.99),
(19, 1, 1, 8.99), (19, 3, 1, 12.99), (19, 6, 1, 3.99),
(20, 4, 2, 11.99), (20, 9, 2, 5.49),
(21, 1, 2, 8.99), (21, 2, 1, 10.99), (21, 5, 1, 10.99),
(22, 3, 2, 12.99), (22, 7, 1, 4.99),
(23, 1, 1, 8.99), (23, 4, 1, 11.99), (23, 8, 2, 2.99),
(24, 2, 3, 10.99), (24, 6, 3, 3.99), (24, 14, 1, 4.49),
(25, 5, 2, 10.99), (25, 10, 2, 6.99), (25, 15, 1, 7.99);

-- Generate more order items for remaining orders (26-60)
INSERT INTO raw_jaffle_shop.order_items (order_id, product_id, quantity, unit_price)
SELECT
    o.id as order_id,
    (RANDOM() * 14 + 1)::INT as product_id,
    (RANDOM() * 2 + 1)::INT as quantity,
    CASE
        WHEN (RANDOM() * 14 + 1)::INT <= 5 THEN 8.99 + RANDOM() * 4
        WHEN (RANDOM() * 14 + 1)::INT <= 10 THEN 2.99 + RANDOM() * 4
        ELSE 4.99 + RANDOM() * 3
    END as unit_price
FROM raw_jaffle_shop.orders o
CROSS JOIN generate_series(1, 2)
WHERE o.id > 25 AND o.id <= 60;

-- =============================================================================
-- SEED DATA: Payments
-- =============================================================================

INSERT INTO raw_stripe.payments (order_id, payment_method, amount, status, created_at, card_last_four, card_brand, billing_email, ip_address, risk_score) VALUES
(1, 'credit_card', 23.97, 'success', '2024-01-02 10:16:00', '4242', 'visa', 'mperez@example.com', '192.168.1.100', 15),
(2, 'credit_card', 15.98, 'success', '2024-01-03 12:31:00', '5555', 'mastercard', 'smyers@example.com', '192.168.1.101', 12),
(3, 'credit_card', 31.46, 'success', '2024-01-05 14:46:00', '3782', 'amex', 'kjohnson@example.com', '192.168.1.102', 8),
(4, 'credit_card', 18.97, 'success', '2024-01-08 09:21:00', '4242', 'visa', 'mperez@example.com', '192.168.1.100', 10),
(5, 'paypal', 48.94, 'success', '2024-01-10 16:01:00', NULL, NULL, 'jramirez@example.com', '192.168.1.103', 5),
(6, 'credit_card', 25.17, 'success', '2024-01-12 11:31:00', '4000', 'visa', 'schen@example.com', '192.168.1.104', 18),
(7, 'credit_card', 19.98, 'success', '2024-01-15 13:16:00', '5105', 'mastercard', 'dwilliams@example.com', '192.168.1.105', 22),
(8, 'credit_card', 56.34, 'success', '2024-01-17 15:46:00', '6011', 'discover', 'mgarcia@example.com', '192.168.1.106', 7),
(9, 'apple_pay', 12.99, 'success', '2024-01-19 10:01:00', '4242', 'visa', 'smyers@example.com', '192.168.1.101', 3),
(10, 'credit_card', 31.97, 'success', '2024-01-22 12:21:00', '5555', 'mastercard', 'jdavis@example.com', '192.168.1.107', 11),
-- Failed and refunded payments for variety
(11, 'credit_card', 24.98, 'failed', '2024-01-24 14:11:00', '4000', 'visa', 'randerson@example.com', '192.168.1.108', 85), -- High risk
(11, 'credit_card', 24.98, 'success', '2024-01-24 14:15:00', '4242', 'visa', 'randerson@example.com', '192.168.1.108', 25), -- Retry
(12, 'credit_card', 35.96, 'success', '2024-01-26 16:31:00', '3782', 'amex', 'ataylor@example.com', '192.168.1.109', 9),
(13, 'paypal', 21.98, 'success', '2024-01-28 09:46:00', NULL, NULL, 'kjohnson@example.com', '192.168.1.102', 4),
(14, 'credit_card', 28.97, 'success', '2024-01-30 11:16:00', '4242', 'visa', 'schen@example.com', '192.168.1.104', 13),
-- Continue with remaining orders
(15, 'credit_card', 33.96, 'success', '2024-02-01 10:31:00', '5555', 'mastercard', 'mperez@example.com', '192.168.1.100', 10),
(16, 'credit_card', 47.34, 'success', '2024-02-02 12:01:00', '4242', 'visa', 'jramirez@example.com', '192.168.1.103', 8),
(17, 'apple_pay', 22.98, 'success', '2024-02-03 14:16:00', '4242', 'visa', 'dwilliams@example.com', '192.168.1.105', 5),
(18, 'credit_card', 17.98, 'success', '2024-02-05 09:01:00', '6011', 'discover', 'unknown@test.com', '10.0.0.1', 45),
(19, 'credit_card', 29.97, 'success', '2024-02-06 11:31:00', '5105', 'mastercard', 'duplicate@example.com', '192.168.1.110', 15),
(20, 'paypal', 35.06, 'success', '2024-02-08 13:46:00', NULL, NULL, 'mgarcia@example.com', '192.168.1.106', 6);

-- Generate payments for remaining orders
INSERT INTO raw_stripe.payments (order_id, payment_method, amount, status, created_at, card_last_four, card_brand, billing_email, ip_address, risk_score)
SELECT
    o.id,
    CASE (RANDOM() * 3)::INT
        WHEN 0 THEN 'credit_card'
        WHEN 1 THEN 'paypal'
        ELSE 'apple_pay'
    END,
    o.order_total - o.discount_amount + o.shipping_cost,
    CASE WHEN o.status IN ('cancelled', 'return_pending') THEN 'refunded' ELSE 'success' END,
    o.created_at + INTERVAL '1 minute',
    CASE WHEN (RANDOM() * 3)::INT = 1 THEN NULL ELSE (1000 + (RANDOM() * 8999)::INT)::TEXT END,
    CASE (RANDOM() * 3)::INT WHEN 0 THEN 'visa' WHEN 1 THEN 'mastercard' ELSE 'amex' END,
    c.email,
    ('192.168.1.' || (100 + c.id))::INET,
    (RANDOM() * 50)::INT
FROM raw_jaffle_shop.orders o
LEFT JOIN raw_jaffle_shop.customers c ON o.customer_id = c.id
WHERE o.id > 20 AND o.order_total IS NOT NULL;

-- =============================================================================
-- SEED DATA: Refunds
-- =============================================================================

INSERT INTO raw_stripe.refunds (payment_id, amount, reason, status, created_at) VALUES
(3, 5.00, 'Item damaged', 'completed', '2024-01-10 10:00:00'),
(8, 12.99, 'Wrong item sent', 'completed', '2024-01-25 14:30:00'),
(12, 35.96, 'Customer cancelled', 'completed', '2024-01-28 09:00:00'),
(15, 8.99, 'Quality issue', 'pending', '2024-02-05 11:00:00');

-- =============================================================================
-- SEED DATA: Marketing Campaigns
-- =============================================================================

INSERT INTO raw_marketing.campaigns (name, channel, start_date, end_date, budget, target_audience, status, created_by) VALUES
('New Year Launch', 'email', '2024-01-01', '2024-01-15', 5000.00, 'All customers', 'completed', 'marketing@jaffle.shop'),
('Winter Warmup', 'social', '2024-01-10', '2024-01-31', 3500.00, 'Cold regions', 'completed', 'marketing@jaffle.shop'),
('Valentine Special', 'email', '2024-02-07', '2024-02-14', 4000.00, 'Couples', 'completed', 'marketing@jaffle.shop'),
('Spring Forward', 'paid_search', '2024-03-01', '2024-03-31', 7500.00, 'New customers', 'completed', 'marketing@jaffle.shop'),
('Loyalty Rewards', 'email', '2024-03-15', NULL, 2000.00, 'Repeat customers', 'active', 'marketing@jaffle.shop'),
('Social Buzz', 'social', '2024-04-01', NULL, 5000.00, 'Millennials', 'active', 'marketing@jaffle.shop'),
('Google Ads Q2', 'paid_search', '2024-04-01', '2024-06-30', 15000.00, 'High intent', 'active', 'marketing@jaffle.shop');

-- =============================================================================
-- SEED DATA: Ad Spend
-- =============================================================================

INSERT INTO raw_marketing.ad_spend (campaign_id, spend_date, impressions, clicks, conversions, spend_amount, platform)
SELECT
    c.id,
    d::DATE,
    (5000 + RANDOM() * 15000)::INT,
    (100 + RANDOM() * 500)::INT,
    (5 + RANDOM() * 30)::INT,
    (c.budget / 30.0) * (0.8 + RANDOM() * 0.4),
    CASE c.channel
        WHEN 'email' THEN 'Mailchimp'
        WHEN 'social' THEN CASE (RANDOM() * 2)::INT WHEN 0 THEN 'Facebook' WHEN 1 THEN 'Instagram' ELSE 'TikTok' END
        WHEN 'paid_search' THEN CASE (RANDOM() * 1)::INT WHEN 0 THEN 'Google Ads' ELSE 'Bing Ads' END
    END
FROM raw_marketing.campaigns c
CROSS JOIN generate_series(c.start_date, COALESCE(c.end_date, CURRENT_DATE), '1 day'::INTERVAL) d;

-- =============================================================================
-- SEED DATA: User Sessions
-- =============================================================================

INSERT INTO raw_marketing.user_sessions (session_id, customer_id, started_at, ended_at, page_views, utm_source, utm_medium, utm_campaign, device_type, browser, ip_address, country, region)
SELECT
    'sess_' || md5(RANDOM()::TEXT),
    CASE WHEN RANDOM() > 0.3 THEN (1 + (RANDOM() * 24)::INT) ELSE NULL END,
    ts,
    ts + (INTERVAL '1 minute' * (5 + (RANDOM() * 30)::INT)),
    (2 + RANDOM() * 15)::INT,
    CASE (RANDOM() * 5)::INT
        WHEN 0 THEN 'google' WHEN 1 THEN 'facebook' WHEN 2 THEN 'email'
        WHEN 3 THEN 'direct' ELSE 'referral' END,
    CASE (RANDOM() * 4)::INT
        WHEN 0 THEN 'cpc' WHEN 1 THEN 'organic' WHEN 2 THEN 'email' ELSE 'social' END,
    CASE (RANDOM() * 3)::INT
        WHEN 0 THEN 'spring_sale' WHEN 1 THEN 'loyalty' ELSE NULL END,
    CASE (RANDOM() * 2)::INT WHEN 0 THEN 'mobile' WHEN 1 THEN 'desktop' ELSE 'tablet' END,
    CASE (RANDOM() * 3)::INT WHEN 0 THEN 'Chrome' WHEN 1 THEN 'Safari' WHEN 2 THEN 'Firefox' ELSE 'Edge' END,
    ('192.168.' || (RANDOM() * 255)::INT || '.' || (RANDOM() * 255)::INT)::INET,
    'USA',
    CASE (RANDOM() * 5)::INT
        WHEN 0 THEN 'California' WHEN 1 THEN 'Texas' WHEN 2 THEN 'New York'
        WHEN 3 THEN 'Florida' ELSE 'Washington' END
FROM generate_series('2024-01-01'::TIMESTAMP, '2024-04-16'::TIMESTAMP, '2 hours'::INTERVAL) ts;

-- =============================================================================
-- SEED DATA: Support Tickets
-- =============================================================================

INSERT INTO raw_support.tickets (customer_id, order_id, subject, description, priority, status, category, assigned_to, created_at, resolved_at, satisfaction_score) VALUES
(1, 1, 'Order arrived cold', 'My jaffle was cold when it arrived', 'medium', 'resolved', 'delivery', 'support@jaffle.shop', '2024-01-03 14:00:00', '2024-01-03 16:30:00', 4),
(3, 3, 'Missing item', 'One drink was missing from my order', 'high', 'resolved', 'order_issue', 'support@jaffle.shop', '2024-01-06 10:00:00', '2024-01-06 11:00:00', 5),
(5, 6, 'Billing question', 'Why was I charged twice?', 'high', 'resolved', 'billing', 'billing@jaffle.shop', '2024-01-13 09:00:00', '2024-01-13 10:30:00', 5),
(7, 8, 'T-shirt size exchange', 'Need to exchange for larger size', 'low', 'resolved', 'returns', 'support@jaffle.shop', '2024-01-20 11:00:00', '2024-01-25 14:00:00', 4),
(8, 10, 'Late delivery', 'Order took over an hour', 'medium', 'resolved', 'delivery', 'support@jaffle.shop', '2024-01-22 13:00:00', '2024-01-22 15:00:00', 3),
(10, 12, 'Refund request', 'Food quality not as expected', 'high', 'resolved', 'refund', 'support@jaffle.shop', '2024-01-27 16:00:00', '2024-01-28 10:00:00', 4),
(12, 19, 'Coupon not applied', 'My SAVE10 code didnt work', 'medium', 'resolved', 'billing', 'billing@jaffle.shop', '2024-02-07 09:30:00', '2024-02-07 10:00:00', 5),
(14, 24, 'Allergy concern', 'Does the veggie jaffle contain nuts?', 'high', 'resolved', 'product_info', 'support@jaffle.shop', '2024-02-15 08:00:00', '2024-02-15 08:30:00', 5),
(16, 30, 'Wrong order', 'Received someone elses order', 'high', 'resolved', 'order_issue', 'support@jaffle.shop', '2024-03-02 12:00:00', '2024-03-02 13:30:00', 4),
(18, 34, 'Delivery address change', 'Need to update delivery address', 'medium', 'open', 'delivery', NULL, '2024-03-08 10:00:00', NULL, NULL),
(20, 38, 'Payment declined', 'Card keeps getting declined', 'high', 'open', 'billing', 'billing@jaffle.shop', '2024-03-16 14:00:00', NULL, NULL),
(1, 46, 'Feedback', 'The new spicy jaffle is amazing!', 'low', 'resolved', 'feedback', 'support@jaffle.shop', '2024-03-28 11:00:00', '2024-03-28 11:30:00', 5);

-- =============================================================================
-- SEED DATA: Product Reviews
-- =============================================================================

INSERT INTO raw_support.reviews (product_id, customer_id, order_id, rating, title, review_text, is_verified_purchase, helpful_votes, created_at) VALUES
(1, 1, 1, 5, 'Perfect comfort food', 'The classic jaffle is exactly what I remember from childhood. Perfectly toasted!', TRUE, 12, '2024-01-05'),
(2, 3, 3, 4, 'Great veggie option', 'Love the variety of vegetables. Could use a bit more cheese though.', TRUE, 8, '2024-01-08'),
(3, 4, 5, 5, 'Meat lovers dream', 'So much meat! The perfect lunch after a workout.', TRUE, 15, '2024-01-12'),
(1, 2, 2, 4, 'Good but basic', 'Solid choice but nothing extraordinary. Good value for money.', TRUE, 5, '2024-01-06'),
(4, 7, 8, 5, 'Spice is right', 'Finally a place that knows how to do spicy food! Will order again.', TRUE, 20, '2024-01-20'),
(5, 8, 10, 4, 'Breakfast champion', 'Great way to start the day. Eggs could be a bit runnier.', TRUE, 7, '2024-01-25'),
(6, 5, 6, 5, 'Refreshing!', 'Best lemonade Ive had. Real lemons make all the difference.', TRUE, 18, '2024-01-15'),
(8, 9, 11, 3, 'Just okay coffee', 'Decent coffee but Ive had better. A bit weak for my taste.', TRUE, 4, '2024-01-26'),
(16, 7, 8, 5, 'Love the merch', 'Great quality t-shirt. Fits perfectly and the design is cool.', TRUE, 11, '2024-01-22'),
(10, 10, 12, 4, 'Healthy and tasty', 'Surprised how good this smoothie is. Very filling too.', TRUE, 9, '2024-01-28'),
(14, 6, 7, 5, 'Brownie perfection', 'Rich, fudgy, and not too sweet. Pairs great with coffee.', TRUE, 14, '2024-01-18'),
(15, 14, 24, 5, 'Desert jaffle ftw', 'Didnt know I needed this in my life. Apple pie in jaffle form!', TRUE, 22, '2024-02-16'),
-- Some negative reviews for realism
(3, 11, 18, 2, 'Disappointing', 'Too greasy and the bread was soggy. Expected better.', TRUE, 3, '2024-02-08'),
(7, 12, 19, 2, 'Burnt coffee', 'Coffee tasted burnt. Maybe a bad batch?', TRUE, 6, '2024-02-09'),
-- Unverified reviews (data quality scenario)
(1, NULL, NULL, 5, 'Amazing!', 'Best jaffles ever!', FALSE, 2, '2024-02-20'),
(2, NULL, NULL, 1, 'Terrible', 'Worst food I ever had', FALSE, 0, '2024-02-25');

-- =============================================================================
-- ANALYTICS VIEWS (pre-built for BI tools)
-- =============================================================================

-- Daily revenue summary
CREATE VIEW analytics.daily_revenue AS
SELECT
    o.order_date,
    COUNT(DISTINCT o.id) as total_orders,
    COUNT(DISTINCT o.customer_id) as unique_customers,
    SUM(o.order_total) as gross_revenue,
    SUM(o.discount_amount) as total_discounts,
    SUM(o.shipping_cost) as shipping_revenue,
    SUM(o.order_total - o.discount_amount + o.shipping_cost) as net_revenue,
    AVG(o.order_total) as avg_order_value
FROM raw_jaffle_shop.orders o
WHERE o.status = 'completed'
GROUP BY o.order_date
ORDER BY o.order_date;

-- Customer lifetime value
CREATE VIEW analytics.customer_ltv AS
SELECT
    c.id as customer_id,
    c.first_name || ' ' || c.last_name as customer_name,
    c.email,
    c.created_at as customer_since,
    COUNT(DISTINCT o.id) as total_orders,
    SUM(o.order_total) as lifetime_value,
    AVG(o.order_total) as avg_order_value,
    MIN(o.order_date) as first_order_date,
    MAX(o.order_date) as last_order_date,
    MAX(o.order_date) - MIN(o.order_date) as customer_tenure_days
FROM raw_jaffle_shop.customers c
LEFT JOIN raw_jaffle_shop.orders o ON c.id = o.customer_id AND o.status = 'completed'
GROUP BY c.id, c.first_name, c.last_name, c.email, c.created_at;

-- Product performance
CREATE VIEW analytics.product_performance AS
SELECT
    p.id as product_id,
    p.sku,
    p.name as product_name,
    p.category,
    p.subcategory,
    COUNT(DISTINCT oi.order_id) as times_ordered,
    SUM(oi.quantity) as units_sold,
    SUM(oi.quantity * oi.unit_price) as total_revenue,
    AVG(r.rating) as avg_rating,
    COUNT(DISTINCT r.id) as review_count
FROM raw_inventory.products p
LEFT JOIN raw_jaffle_shop.order_items oi ON p.id = oi.product_id
LEFT JOIN raw_support.reviews r ON p.id = r.product_id
GROUP BY p.id, p.sku, p.name, p.category, p.subcategory;

-- Marketing campaign ROI
CREATE VIEW analytics.campaign_roi AS
SELECT
    c.id as campaign_id,
    c.name as campaign_name,
    c.channel,
    c.budget,
    SUM(a.spend_amount) as total_spend,
    SUM(a.impressions) as total_impressions,
    SUM(a.clicks) as total_clicks,
    SUM(a.conversions) as total_conversions,
    CASE WHEN SUM(a.impressions) > 0
        THEN ROUND(SUM(a.clicks)::DECIMAL / SUM(a.impressions) * 100, 2)
        ELSE 0 END as ctr_percent,
    CASE WHEN SUM(a.clicks) > 0
        THEN ROUND(SUM(a.conversions)::DECIMAL / SUM(a.clicks) * 100, 2)
        ELSE 0 END as conversion_rate,
    CASE WHEN SUM(a.conversions) > 0
        THEN ROUND(SUM(a.spend_amount) / SUM(a.conversions), 2)
        ELSE 0 END as cost_per_conversion
FROM raw_marketing.campaigns c
LEFT JOIN raw_marketing.ad_spend a ON c.id = a.campaign_id
GROUP BY c.id, c.name, c.channel, c.budget;

-- =============================================================================
-- PERMISSIONS & EXTENSIONS FOR OPENMETADATA
-- =============================================================================

-- Enable pg_stat_statements for query lineage tracking
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Grant schema usage and table access
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA raw_jaffle_shop TO jaffle_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA raw_stripe TO jaffle_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA raw_inventory TO jaffle_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA raw_marketing TO jaffle_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA raw_support TO jaffle_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA analytics TO jaffle_user;
GRANT USAGE ON SCHEMA raw_jaffle_shop, raw_stripe, raw_inventory, raw_marketing, raw_support, analytics TO jaffle_user;

-- dbt schemas: jaffle_user needs CREATE + USAGE to run dbt models
GRANT ALL ON SCHEMA staging, intermediate, marts_core, marts_finance, marts_marketing TO jaffle_user;

-- Grant permissions for OpenMetadata lineage extraction
-- pg_stat_statements requires pg_read_all_stats role for non-superusers
GRANT pg_read_all_stats TO jaffle_user;

-- Grant access to system catalogs needed for metadata extraction
GRANT SELECT ON ALL TABLES IN SCHEMA pg_catalog TO jaffle_user;
GRANT SELECT ON ALL TABLES IN SCHEMA information_schema TO jaffle_user;

-- Ensure future tables in schemas are also accessible
ALTER DEFAULT PRIVILEGES IN SCHEMA raw_jaffle_shop GRANT ALL ON TABLES TO jaffle_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw_stripe GRANT ALL ON TABLES TO jaffle_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw_inventory GRANT ALL ON TABLES TO jaffle_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw_marketing GRANT ALL ON TABLES TO jaffle_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw_support GRANT ALL ON TABLES TO jaffle_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics GRANT ALL ON TABLES TO jaffle_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA staging GRANT ALL ON TABLES TO jaffle_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA intermediate GRANT ALL ON TABLES TO jaffle_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA marts_core GRANT ALL ON TABLES TO jaffle_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA marts_finance GRANT ALL ON TABLES TO jaffle_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA marts_marketing GRANT ALL ON TABLES TO jaffle_user;

-- Create an openmetadata_user with read-only access (recommended for production)
CREATE USER openmetadata_user WITH PASSWORD 'openmetadata_pass';
GRANT CONNECT ON DATABASE jaffle_shop TO openmetadata_user;
GRANT USAGE ON SCHEMA raw_jaffle_shop, raw_stripe, raw_inventory, raw_marketing, raw_support, analytics, public TO openmetadata_user;
GRANT USAGE ON SCHEMA staging, intermediate, marts_core, marts_finance, marts_marketing TO openmetadata_user;
GRANT SELECT ON ALL TABLES IN SCHEMA raw_jaffle_shop TO openmetadata_user;
GRANT SELECT ON ALL TABLES IN SCHEMA raw_stripe TO openmetadata_user;
GRANT SELECT ON ALL TABLES IN SCHEMA raw_inventory TO openmetadata_user;
GRANT SELECT ON ALL TABLES IN SCHEMA raw_marketing TO openmetadata_user;
GRANT SELECT ON ALL TABLES IN SCHEMA raw_support TO openmetadata_user;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO openmetadata_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO openmetadata_user;
GRANT SELECT ON ALL TABLES IN SCHEMA staging TO openmetadata_user;
GRANT SELECT ON ALL TABLES IN SCHEMA intermediate TO openmetadata_user;
GRANT SELECT ON ALL TABLES IN SCHEMA marts_core TO openmetadata_user;
GRANT SELECT ON ALL TABLES IN SCHEMA marts_finance TO openmetadata_user;
GRANT SELECT ON ALL TABLES IN SCHEMA marts_marketing TO openmetadata_user;
GRANT pg_read_all_stats TO openmetadata_user;
GRANT SELECT ON ALL TABLES IN SCHEMA pg_catalog TO openmetadata_user;
GRANT SELECT ON ALL TABLES IN SCHEMA information_schema TO openmetadata_user;

-- Future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA raw_jaffle_shop GRANT SELECT ON TABLES TO openmetadata_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw_stripe GRANT SELECT ON TABLES TO openmetadata_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw_inventory GRANT SELECT ON TABLES TO openmetadata_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw_marketing GRANT SELECT ON TABLES TO openmetadata_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw_support GRANT SELECT ON TABLES TO openmetadata_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics GRANT SELECT ON TABLES TO openmetadata_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO openmetadata_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA staging GRANT SELECT ON TABLES TO openmetadata_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA intermediate GRANT SELECT ON TABLES TO openmetadata_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA marts_core GRANT SELECT ON TABLES TO openmetadata_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA marts_finance GRANT SELECT ON TABLES TO openmetadata_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA marts_marketing GRANT SELECT ON TABLES TO openmetadata_user;

-- Default privileges for objects created by jaffle_user (dbt runs as jaffle_user)
ALTER DEFAULT PRIVILEGES FOR ROLE jaffle_user IN SCHEMA staging GRANT SELECT ON TABLES TO openmetadata_user;
ALTER DEFAULT PRIVILEGES FOR ROLE jaffle_user IN SCHEMA intermediate GRANT SELECT ON TABLES TO openmetadata_user;
ALTER DEFAULT PRIVILEGES FOR ROLE jaffle_user IN SCHEMA marts_core GRANT SELECT ON TABLES TO openmetadata_user;
ALTER DEFAULT PRIVILEGES FOR ROLE jaffle_user IN SCHEMA marts_finance GRANT SELECT ON TABLES TO openmetadata_user;
ALTER DEFAULT PRIVILEGES FOR ROLE jaffle_user IN SCHEMA marts_marketing GRANT SELECT ON TABLES TO openmetadata_user;

COMMIT;
