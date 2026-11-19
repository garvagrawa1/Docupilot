-- Demo data for the fictional company Northwind Labs (matches data/sample/*.md).
-- All people, emails and phone numbers are made up.

INSERT INTO employees (employee_id, full_name, email, phone, department, job_title, manager_id, location, join_date) VALUES
('E101', 'Ananya Rao',     'ananya.rao@northwind.example',     '+91 98450 12345', 'Engineering',       'Engineering Manager',       NULL,   'Bengaluru', '2019-06-03'),
('E102', 'Rahul Mehta',    'rahul.mehta@northwind.example',    '+91 98201 33445', 'Engineering',       'Backend Engineer',          'E101', 'Bengaluru', '2022-02-14'),
('E103', 'Priya Nair',     'priya.nair@northwind.example',     '+91 99001 77821', 'Engineering',       'Data Scientist',            'E101', 'Remote',    '2023-08-01'),
('E104', 'Vikram Singh',   'vikram.singh@northwind.example',   '+91 98110 45678', 'People Operations', 'HR Business Partner',       NULL,   'Gurugram',  '2018-11-19'),
('E105', 'Sneha Kulkarni', 'sneha.kulkarni@northwind.example', '+91 97300 11223', 'Finance',           'Accounts Executive',        'E104', 'Pune',      '2024-01-08'),
('E106', 'Arjun Das',      'arjun.das@northwind.example',      '+91 90070 98765', 'IT',                'IT Support Lead',           NULL,   'Bengaluru', '2020-04-20'),
('E107', 'Meera Iyer',     'meera.iyer@northwind.example',     '+91 98860 24680', 'Design',            'Product Designer',          'E101', 'Chennai',   '2025-07-01'),
('E108', 'Kabir Khan',     'kabir.khan@northwind.example',     '+91 99870 13579', 'Sales',             'Account Executive',         'E104', 'Mumbai',    '2026-03-02');

-- Leave year 2026. Entitlements follow leave_policy.md: 18 earned, 8 casual, 10 sick (pro-rata for mid-year joiners).
INSERT INTO leave_balances (employee_id, leave_year, leave_type, entitled_days, carried_forward, taken_days) VALUES
('E101', 2026, 'earned', 18, 30, 12),  ('E101', 2026, 'casual', 8, 0, 5),  ('E101', 2026, 'sick', 10, 0, 2),
('E102', 2026, 'earned', 18, 6, 9.5),  ('E102', 2026, 'casual', 8, 0, 3),  ('E102', 2026, 'sick', 10, 0, 4),
('E103', 2026, 'earned', 18, 11, 20),  ('E103', 2026, 'casual', 8, 0, 8),  ('E103', 2026, 'sick', 10, 0, 1),
('E104', 2026, 'earned', 18, 30, 6),   ('E104', 2026, 'casual', 8, 0, 2),  ('E104', 2026, 'sick', 10, 0, 0),
('E105', 2026, 'earned', 18, 2.5, 14), ('E105', 2026, 'casual', 8, 0, 6),  ('E105', 2026, 'sick', 10, 0, 7),
('E106', 2026, 'earned', 18, 15, 3),   ('E106', 2026, 'casual', 8, 0, 1),  ('E106', 2026, 'sick', 10, 0, 3),
('E107', 2026, 'earned', 18, 0, 10),   ('E107', 2026, 'casual', 8, 0, 4),  ('E107', 2026, 'sick', 10, 0, 2),
('E108', 2026, 'earned', 15, 0, 4.5),  ('E108', 2026, 'casual', 7, 0, 2),  ('E108', 2026, 'sick', 8.5, 0, 0);

INSERT INTO it_tickets (ticket_id, employee_id, category, title, status, priority, assigned_team, opened_at, updated_at) VALUES
('IT-1038', 'E102', 'Access',   'VPN disconnects every 20 minutes',          'in_progress', 'high',     'Network',        '2026-11-12 09:40+05:30', '2026-11-18 16:05+05:30'),
('IT-1041', 'E102', 'Hardware', 'Laptop battery swelling',                   'open',        'critical', 'Endpoint',       '2026-11-17 11:20+05:30', '2026-11-17 11:20+05:30'),
('IT-1029', 'E102', 'Software', 'IntelliJ licence renewal',                  'resolved',    'low',      'Software Assets', '2026-10-28 10:00+05:30', '2026-10-30 14:30+05:30'),
('IT-1040', 'E103', 'Access',   'Need read access to the analytics warehouse', 'open',      'medium',   'Data Platform',  '2026-11-15 15:10+05:30', '2026-11-16 09:00+05:30'),
('IT-1035', 'E105', 'Email',    'Phishing email reported',                   'closed',      'high',     'Security',       '2026-11-05 08:55+05:30', '2026-11-05 12:10+05:30'),
('IT-1042', 'E107', 'Hardware', 'Second monitor request',                    'open',        'low',      'Endpoint',       '2026-11-18 13:45+05:30', '2026-11-18 13:45+05:30'),
('IT-1037', 'E108', 'Access',   'MFA reset after phone change',              'resolved',    'medium',   'Identity',       '2026-11-10 17:30+05:30', '2026-11-11 10:15+05:30'),
('IT-1043', 'E101', 'Software', 'Slack desktop app crashes on start',        'in_progress', 'medium',   'Software Assets', '2026-11-19 09:05+05:30', '2026-11-19 10:20+05:30');
