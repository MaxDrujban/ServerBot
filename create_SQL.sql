-- =============================================
-- Создание базы данных и таблиц
-- PostgreSQL - Домоуправление (Вариант 15)
-- =============================================

-- Создание таблиц

-- 1. Владельцы
CREATE TABLE Owners (
    owner_id    SERIAL PRIMARY KEY,
    full_name   VARCHAR(100) NOT NULL,
    phone       VARCHAR(45),
    email       VARCHAR(45)
);

-- 2. Квартиры
CREATE TABLE Apartment (
    apartment_id    SERIAL PRIMARY KEY,
    apartment_number INT NOT NULL,
    house_number    VARCHAR(20) NOT NULL,
    street          VARCHAR(100) NOT NULL,
    city            VARCHAR(45) DEFAULT 'Москва',
    owner_id        INT,
    
    CONSTRAINT fk_apartment_owner 
        FOREIGN KEY (owner_id) REFERENCES Owners(owner_id) 
        ON DELETE SET NULL
);

-- 3. Услуги
CREATE TABLE Service (
    service_id     SERIAL PRIMARY KEY,
    service_name   VARCHAR(100) NOT NULL,
    has_meter      BOOLEAN DEFAULT FALSE,
    monthly_price  DECIMAL(10,2)
);

-- 4. Показания счетчиков
CREATE TABLE MeterReading (
    reading_id      SERIAL PRIMARY KEY,
    apartment_id    INT NOT NULL,
    service_id      INT NOT NULL,
    reading_date    DATE NOT NULL,
    previous_value  DECIMAL(12,3),
    current_value   DECIMAL(12,3) NOT NULL,
    
    CONSTRAINT fk_meter_apartment 
        FOREIGN KEY (apartment_id) REFERENCES Apartment(apartment_id) ON DELETE CASCADE,
        
    CONSTRAINT fk_meter_service 
        FOREIGN KEY (service_id) REFERENCES Service(service_id)
);

-- 5. Платежи
CREATE TABLE Payment (
    payment_id     SERIAL PRIMARY KEY,
    apartment_id   INT NOT NULL,
    service_id     INT NOT NULL,
    year           INT NOT NULL,
    month          INT NOT NULL CHECK (month BETWEEN 1 AND 12),
    amount         DECIMAL(10,2) NOT NULL,
    paid_amount    DECIMAL(10,2) DEFAULT 0,
    payment_date   DATE,
    status         VARCHAR(20) DEFAULT 'pending' 
                   CHECK (status IN ('pending', 'paid', 'overdue', 'partial')),
    
    CONSTRAINT fk_payment_apartment 
        FOREIGN KEY (apartment_id) REFERENCES Apartment(apartment_id) ON DELETE CASCADE,
        
    CONSTRAINT fk_payment_service 
        FOREIGN KEY (service_id) REFERENCES Service(service_id)
);

-- =============================================
-- Создание индексов для ускорения поиска
-- =============================================

CREATE INDEX idx_apartment_owner ON Apartment(owner_id);
CREATE INDEX idx_meter_apartment ON MeterReading(apartment_id);
CREATE INDEX idx_meter_service ON MeterReading(service_id);
CREATE INDEX idx_payment_apartment ON Payment(apartment_id);
CREATE INDEX idx_payment_status ON Payment(status);