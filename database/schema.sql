
CREATE DATABASE IF NOT EXISTS collegeconnect;
USE collegeconnect;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('student','professor','cr','admin') NOT NULL,
    branch VARCHAR(20),
    year_level VARCHAR(10),
    division VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS classrooms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    location VARCHAR(30) UNIQUE NOT NULL,
    block VARCHAR(20),
    room_number VARCHAR(20),
    capacity INT NULL,
    has_ac BOOLEAN DEFAULT FALSE,
    has_smart_board BOOLEAN DEFAULT FALSE,
    has_wifi BOOLEAN DEFAULT FALSE,
    status ENUM('available','occupied','maintenance','inactive') DEFAULT 'available'
);

CREATE TABLE IF NOT EXISTS timetable (
    id INT AUTO_INCREMENT PRIMARY KEY,
    branch VARCHAR(20) NOT NULL,
    year_level VARCHAR(10) NOT NULL,
    division VARCHAR(10) NOT NULL,
    day VARCHAR(15) NOT NULL,
    time_slot VARCHAR(30) NOT NULL,
    subject_code VARCHAR(30) NOT NULL,
    prof_code VARCHAR(30) NOT NULL,
    location VARCHAR(30) NOT NULL
);

CREATE TABLE IF NOT EXISTS complaints (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category VARCHAR(50) NOT NULL,
    location VARCHAR(30),
    title VARCHAR(150) NOT NULL,
    description TEXT NOT NULL,
    priority ENUM('low','medium','high','critical') DEFAULT 'medium',
    status ENUM('pending','in_progress','resolved') DEFAULT 'pending',
    reported_by INT NULL,
    assigned_to INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL,
    FOREIGN KEY (reported_by) REFERENCES users(id),
    FOREIGN KEY (assigned_to) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS complaint_updates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    complaint_id INT NOT NULL,
    updated_by INT NULL,
    old_status VARCHAR(30),
    new_status VARCHAR(30),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (complaint_id) REFERENCES complaints(id),
    FOREIGN KEY (updated_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
