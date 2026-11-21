-- Parâmetros Psycopg. O fim do período é inclusivo em UTC.
-- Distância epicentral sobre o elipsoide WGS 84, em quilômetros.
WITH alvo AS (
    SELECT id, nome, geometria, geometria::geography AS geog
    FROM barragens WHERE id = %(id)s
), eventos AS MATERIALIZED (
    SELECT t.id, t.codigo_origem, t.data_hora, t.magnitude, t.profundidade_km,
           f.nome fonte, f.endereco_url fonte_url, f.data_coleta, f.versao fonte_versao,
           ST_AsGeoJSON(t.geometria)::jsonb geometry,
           ST_Distance(t.geometria::geography, a.geog) / 1000.0 AS distancia_km
    FROM alvo a
    JOIN eventos_sismicos t ON ST_DWithin(t.geometria::geography, a.geog, %(metros)s)
    JOIN fontes_dados f ON f.id=t.fonte_id
    WHERE t.magnitude >= %(magnitude)s
      AND (%(inicio)s::date IS NULL OR t.data_hora >= %(inicio)s::date)
      AND (%(fim)s::date IS NULL OR t.data_hora < (%(fim)s::date + 1))
), anual AS (
    SELECT EXTRACT(YEAR FROM data_hora AT TIME ZONE 'UTC')::integer ano, count(*) total
    FROM eventos GROUP BY 1
), pagina AS (
    SELECT * FROM eventos ORDER BY distancia_km, id LIMIT %(limite)s OFFSET %(offset)s
)
SELECT a.id, a.nome, ST_AsGeoJSON(a.geometria)::jsonb geometry,
       (SELECT count(*) FROM eventos) total,
       (SELECT min(distancia_km) FROM eventos) menor_distancia_km,
       (SELECT max(magnitude) FROM eventos) maior_magnitude,
       (SELECT COALESCE(jsonb_agg(to_jsonb(anual) ORDER BY ano), '[]') FROM anual) por_ano,
       (SELECT COALESCE(jsonb_agg(jsonb_build_object(
            'type', 'Feature', 'id', id, 'geometry', geometry,
            'properties', to_jsonb(pagina) - 'geometry' - 'id'
        ) ORDER BY distancia_km, id), '[]') FROM pagina) eventos,
       (SELECT COALESCE(jsonb_agg(jsonb_build_object(
            'nome', z.nome, 'referencia', z.referencia_cientifica, 'metodologia', z.metodologia
        ) ORDER BY z.nome), '[]')
        FROM zonas_sismogenicas z WHERE ST_Intersects(z.geometria, a.geometria)) zonas
FROM alvo a;

