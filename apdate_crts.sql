



CREATE TABLE public.rescue_events (
    event_id SERIAL PRIMARY KEY,
    
    event_number VARCHAR(20) NOT NULL UNIQUE,
    event_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    priority VARCHAR(10) DEFAULT 'normal',
    
    -- Localisation
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    location_name VARCHAR(200),
    distance_coast_km DOUBLE PRECISION,
    
    -- Détails de l'incident
    description TEXT,
    reported_by VARCHAR(100),
    report_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    incident_time TIMESTAMP,
    
    -- Personnes impliquées
    persons_involved INTEGER DEFAULT 1,
    persons_rescued INTEGER DEFAULT 0,
    persons_deceased INTEGER DEFAULT 0,
    persons_missing INTEGER DEFAULT 0,
    
    -- Moyens engagés
    assets_deployed JSON DEFAULT '[]',
    assets_available JSON DEFAULT '[]',
    
    -- Conditions environnementales
    wind_speed DOUBLE PRECISION,
    wind_direction DOUBLE PRECISION,
    current_speed DOUBLE PRECISION,
    current_direction DOUBLE PRECISION,
    sea_state INTEGER,
    visibility_km DOUBLE PRECISION,
    water_temperature DOUBLE PRECISION,
    
    -- Informations navire
    vessel_name VARCHAR(100),
    vessel_type VARCHAR(50),
    vessel_flag VARCHAR(50),
    vessel_imo VARCHAR(20),
    vessel_mmsi VARCHAR(20),
    
    -- Gestion
    created_by INTEGER,
    assigned_to INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    
    -- Détails supplémentaires
    attachments JSON DEFAULT '[]',
    notes TEXT,
    action_log JSON DEFAULT '[]',
    
    -- Clés étrangères
    CONSTRAINT fk_created_by
        FOREIGN KEY (created_by)
        REFERENCES mrcc.users(id)
        ON DELETE SET NULL,
        
    CONSTRAINT fk_assigned_to
        FOREIGN KEY (assigned_to)
        REFERENCES mrcc.users(id)
        ON DELETE SET NULL
);