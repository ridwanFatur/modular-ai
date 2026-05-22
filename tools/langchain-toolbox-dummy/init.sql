CREATE TABLE hotels(
  id            INTEGER NOT NULL PRIMARY KEY,
  name          VARCHAR NOT NULL,
  location      VARCHAR NOT NULL,
  price_tier    VARCHAR NOT NULL,
  booked        BIT     NOT NULL
);

INSERT INTO hotels(id, name, location, price_tier, booked)
VALUES
  (1, 'Hilton Basel', 'Basel', 'Luxury', B'0'),
  (2, 'Marriott Zurich', 'Zurich', 'Upscale', B'0'),
  (3, 'Hyatt Regency Basel', 'Basel', 'Upper Upscale', B'0');