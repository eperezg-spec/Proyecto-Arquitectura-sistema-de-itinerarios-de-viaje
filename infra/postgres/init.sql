-- Una base de datos (y un usuario) POR SERVICIO. Ningún servicio lee la BD de otro.
CREATE USER itinerary_user WITH PASSWORD 'itinerary_pass';
CREATE DATABASE itinerary_db OWNER itinerary_user;

CREATE USER notification_user WITH PASSWORD 'notification_pass';
CREATE DATABASE notification_db OWNER notification_user;
