"""Import current-MDD, previously missing Table 4 taxa from Grunwald et al. (2024)."""
import csv, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent; OUT=ROOT/'data'/'calls'/'grunwald-2024.csv'; RAW=ROOT/'data'/'raw'/'grunwald-2024.pdf'
HASH='0168e6a26a1a006a1069707ded5b2163fd06621dff2c34d7df6f984f7c713861'
FIELDS='observation_id mdd_id verbatim_taxon_name taxon_match_method reference_id locator method_id call_phase call_variant variant_label signal_direction recording_condition habitat_class country locality date_or_season n_individuals n_calls parameter statistic value value_min value_max unit dispersion_type dispersion_value verbatim_value quality_flag notes'.split()
# (slug, MDD id, published name, match, individuals, pulses, peak/sd, min/sd, max/sd, duration/sd)
T=[
('hipposideros-beatus','1004579','Hipposideros beatus','exact',4,162,(129.4,4.0),(114.3,8.4),(132.1,4.5),(5.4,1.5)),
('hipposideros-curtus','1004590','Hipposideros curtus','exact',2,79,(97.0,4.5),(90.0,4.6),(98.2,5.0),(11.0,.4)),
('hipposideros-fuliginosus','1004598','Hipposideros fuliginosus','exact',2,61,(109.9,.2),(92.6,6.0),(111.1,.1),(6.0,1.6)),
('glauconycteris-argentata','1005536','Glauconycteris argentata','exact',2,41,(42.5,.5),(40.6,.1),(75.1,4.3),(1.7,.1)),
('glauconycteris-egeria','1005540','Glauconycteris egeria','exact',2,24,(26.3,2.5),(22.0,2.1),(53.8,2.6),(2.6,.6)),
('afropipistrellus-happoldorum','1005750','Nycticeinops happoldorum','manual',3,27,(46.8,1.6),(41.2,1.6),(87.4,10.4),(2.2,.2)),
('pipistrellus-nanulus','1005627','Pipistrellus nanulus','exact',2,27,(57.3,.6),(54.0,1.6),(106.0,6.0),(2.4,.3)),
('pseudoromicia-mbamminkom','1006740','Pseudoromicia mbamminkom','exact',1,22,(41.6,2.4),(34.2,.8),(58.4,1.5),(2.5,.3)),
('pseudoromicia-roseveari','1005775','Pseudoromicia roseveari','exact',2,20,(39.9,2.6),(37.9,1.2),(53.1,6.1),(2.0,.3)),
]
def main():
 if hashlib.sha256(RAW.read_bytes()).hexdigest()!=HASH: raise SystemExit('raw hash changed; re-audit')
 rows=[]
 for slug,mdd,taxon,match,indiv,n,*vals in T:
  for par,(value,sd) in zip(('peak_frequency','min_frequency','max_frequency','duration'),vals):
   unit='ms' if par=='duration' else 'kHz'; r={f:'' for f in FIELDS}; r.update(observation_id='grunwald-2024-'+slug,mdd_id=mdd,verbatim_taxon_name=taxon,taxon_match_method=match,reference_id='grunwald-2024',locator=f'Table 4, {taxon} row',method_id='grunwald-2024-full-spectrum',call_phase='unspecified',recording_condition='free_flying_wild',country='Cameroon',locality='Mbam Minkom Massif',date_or_season='2019 and 2022',n_individuals=str(indiv),n_calls=str(n),parameter=par,statistic='mean',value=str(value),unit=unit,dispersion_type='sd',dispersion_value=str(sd),verbatim_value=f'{value} ± {sd}',quality_flag='ok',notes=f'Manually transcribed from Table 4; cached raw SHA-256 {HASH}.') ; rows.append(r)
 with OUT.open('w',encoding='utf-8',newline='') as f: w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
 print(f'Wrote {len(rows)} Grunwald rows')
if __name__=='__main__': main()
