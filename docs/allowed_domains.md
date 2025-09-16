# Allowed Domains Documentation

## Overview

The Health Assistant system restricts web searches and content fetching to a curated list of trusted medical domains. This ensures that all information provided comes from authoritative, evidence-based sources while preventing the system from accessing unreliable or potentially harmful medical information.

## Domain Configuration

**Location:** `src/config/domains.yaml`

The system maintains two domain lists:
1. **trusted_domains**: 119 standard medical domains for patient assistant
2. **provider_domains**: 76 additional specialized domains for provider assistant

**Total Unique Domains:** 169 (after deduplication)

## Domain Categories

### Canadian Health Authorities (26 domains)
Primary sources for Canadian users, especially Ontario-focused content:

#### Provincial/Federal Health Authorities
- **ontario.ca** - Government of Ontario health information
- **publichealthontario.ca** - Public Health Ontario
- **hqontario.ca** - Health Quality Ontario  
- **ontariohealth.ca** - Ontario Health
- **canada.ca** - Government of Canada health section
- **phac-aspc.gc.ca** - Public Health Agency of Canada

#### Medical Regulatory Bodies
- **cpso.on.ca** - College of Physicians and Surgeons of Ontario
- **cma.ca** - Canadian Medical Association
- **cmaj.ca** - Canadian Medical Association Journal

#### Major Canadian Hospitals
- **uhn.ca** - University Health Network (Toronto)
- **sickkids.ca** - The Hospital for Sick Children
- **sunnybrook.ca** - Sunnybrook Health Sciences Centre
- **stmichaelshospital.com** - St. Michael's Hospital
- **hamiltonhealthsciences.ca** - Hamilton Health Sciences
- **theottawahospital.on.ca** - The Ottawa Hospital

#### Provincial Health Services
- **healthlinkbc.ca** - HealthLink BC
- **ahs.ca** - Alberta Health Services
- **saskhealthauthority.ca** - Saskatchewan Health Authority
- **nshealth.ca** - Nova Scotia Health

### Canadian Disease-Specific Organizations (12 domains)
Specialty organizations providing disease-specific information:

- **diabetes.ca** - Diabetes Canada
- **heartandstroke.ca** - Heart and Stroke Foundation
- **cancer.ca** - Canadian Cancer Society
- **alzheimer.ca** - Alzheimer Society of Canada
- **arthritis.ca** - Arthritis Society Canada
- **lung.ca** - Lung Association
- **parkinson.ca** - Parkinson Canada
- **crohnsandcolitis.ca** - Crohn's and Colitis Canada

### U.S. Academic Medical Centers (31 domains)
Leading academic health systems and medical schools:

#### Top-Tier Medical Centers
- **mayoclinic.org** - Mayo Clinic
- **hopkinsmedicine.org** - Johns Hopkins Medicine
- **clevelandclinic.org** - Cleveland Clinic
- **massgeneral.org** - Massachusetts General Hospital
- **brighamandwomens.org** - Brigham and Women's Hospital

#### Major University Medical Centers
- **stanfordhealthcare.org** / **med.stanford.edu** - Stanford Medicine
- **ucsfhealth.org** - UCSF Health
- **dukehealth.org** - Duke Health
- **cuimc.columbia.edu** / **columbiamedicine.org** - Columbia Medicine
- **uchicagomedicine.org** - University of Chicago Medicine
- **nyulangone.org** - NYU Langone Health
- **uofmhealth.org** - University of Michigan Health
- **yalemedicine.org** - Yale Medicine
- **mountsinai.org** - Mount Sinai Health System
- **pennmedicine.org** - Penn Medicine
- **vumc.org** - Vanderbilt University Medical Center

#### Specialty Centers
- **chop.edu** - Children's Hospital of Philadelphia
- **mdanderson.org** - MD Anderson Cancer Center
- **nm.org** - Northwestern Medicine
- **bcm.edu** - Baylor College of Medicine

### Medical Journals and Publications (25 domains)

#### Tier 1 Medical Journals
- **pubmed.ncbi.nlm.nih.gov** - PubMed/MEDLINE database
- **nejm.org** - New England Journal of Medicine
- **thelancet.com** - The Lancet
- **jamanetwork.com** - JAMA Network
- **bmj.com** - BMJ (British Medical Journal)
- **nature.com** - Nature Medicine
- **sciencemag.org** - Science Magazine
- **annals.org** - Annals of Internal Medicine

#### Additional Medical Publishers (Provider-Only)
- **cell.com** - Cell Press journals
- **springer.com** - Springer medical journals
- **wiley.com** - Wiley medical publications
- **oup.com** - Oxford University Press medical journals
- **plos.org** - PLOS (Public Library of Science)
- **frontiersin.org** - Frontiers in Medicine
- **mdpi.com** - MDPI medical journals
- **biomedcentral.com** - BioMed Central

#### Specialty Medical Journals (Provider-Only)
- **ahajournals.org** - American Heart Association journals
- **diabetesjournals.org** - American Diabetes Association journals
- **neurology.org** - Neurology journals
- **gastrojournal.org** - Gastroenterology journals

### Global Health Authorities (6 domains)
International health organizations and regulatory bodies:

- **who.int** - World Health Organization
- **cdc.gov** - U.S. Centers for Disease Control and Prevention
- **nih.gov** - U.S. National Institutes of Health
- **nhs.uk** - UK National Health Service
- **ema.europa.eu** - European Medicines Agency
- **fda.gov** - U.S. Food and Drug Administration

### Evidence-Based Resources (8 domains)
Clinical decision support and evidence synthesis:

#### Clinical Databases
- **uptodate.com** - UpToDate clinical decision support
- **dynamed.com** - DynaMed clinical reference (Provider-Only)
- **clinicalkey.com** - ClinicalKey medical database (Provider-Only)
- **epocrates.com** - Epocrates drug reference (Provider-Only)

#### Evidence Synthesis
- **cochranelibrary.com** - Cochrane systematic reviews
- **guidelines.gov** - Clinical practice guidelines
- **clinicaltrials.gov** - ClinicalTrials.gov registry
- **epistemonikos.org** - Evidence synthesis database (Provider-Only)

### Professional Medical Organizations (12 domains)
Medical specialty societies and professional associations:

#### U.S. Professional Societies
- **aamc.org** - Association of American Medical Colleges
- **ama-assn.org** - American Medical Association
- **aafp.org** - American Academy of Family Physicians
- **acc.org** - American College of Cardiology
- **acog.org** - American College of Obstetricians and Gynecologists
- **aap.org** - American Academy of Pediatrics (Provider-Only)

#### Canadian Professional Organizations
- **cps.ca** - Canadian Paediatric Society
- **sogc.org** - Society of Obstetricians and Gynaecologists of Canada
- **ccs.ca** - Canadian Cardiovascular Society

### Patient Education Sites (3 domains)
Consumer-focused health information:

- **medlineplus.gov** - MedlinePlus (NIH)
- **healthline.com** - Healthline health information
- **webmd.com** - WebMD medical information

### Provider-Specific Domains (76 additional domains)

#### Clinical Practice Tools
- **lexicomp.com** - Lexicomp drug information
- **micromedex.com** - Micromedex clinical database
- **medscape.com** - Medscape clinical reference

#### Drug Information Resources
- **rxlist.com** - RxList drug database
- **drugs.com** - Drugs.com medication reference
- **goodrx.com** - GoodRx drug information
- **accessdata.fda.gov** - FDA drug database

#### Medical Education
- **emedicine.medscape.com** - eMedicine clinical reference
- **teachmeanatomy.info** - Anatomy education
- **kenhub.com** - Medical education platform

#### Research Repositories
- **biorxiv.org** - Biology preprint server
- **medrxiv.org** - Medical preprint server
- **researchgate.net** - Research collaboration platform
- **scholar.google.com** - Google Scholar

#### Imaging and Radiology
- **radiopaedia.org** - Radiopaedia imaging reference
- **rsna.org** - Radiological Society of North America
- **acr.org** - American College of Radiology

#### Laboratory Medicine
- **labcorp.com** - LabCorp laboratory information
- **questdiagnostics.com** - Quest Diagnostics
- **aacc.org** - American Association for Clinical Chemistry

## Domain Selection Criteria

### Inclusion Criteria
1. **Authority**: Government health agencies, academic medical centers, professional societies
2. **Evidence-Based**: Peer-reviewed journals, systematic reviews, clinical guidelines
3. **Reliability**: Established reputation for accurate medical information
4. **Currency**: Regularly updated content with current medical information
5. **Professional Recognition**: Widely cited and referenced by healthcare professionals

### Exclusion Criteria
1. **Commercial Bias**: Sites with primary commercial intent
2. **Non-Peer Reviewed**: Blogs, forums, or unverified content
3. **Alternative Medicine**: Unproven or non-evidence-based treatments
4. **Regional Limitations**: Local/regional sites without broader applicability
5. **Outdated Information**: Sites with stale or historically outdated content

## Web Fetch Behavior

### Domain Filtering Process
1. **Pre-Search Filtering**: Web search results are automatically filtered to prefer trusted domains
2. **Fetch Validation**: All web_fetch requests validate the target URL against the allowed domain list
3. **Rejection Handling**: Requests to non-trusted domains are blocked and logged
4. **Deduplication**: The system removes duplicate domains when combining patient and provider lists

### Citation Sourcing
- **Patient Mode**: Citations come from 119 trusted domains
- **Provider Mode**: Citations can come from all 169 domains (119 + 76 provider-specific)
- **Domain Priority**: Canadian sources prioritized for Canadian users, then U.S., then international

### Unknown Domain Handling
When web_fetch encounters a domain not in the trusted list:
1. **Request Blocked**: The fetch request is rejected
2. **Logging**: The attempt is logged for potential domain list updates
3. **User Notification**: Response may include a note about source limitations
4. **Fallback**: System continues with other available sources

## Quality Assurance

### Domain Monitoring
- **Regular Review**: Domain list reviewed quarterly for additions/removals
- **Access Verification**: Periodic testing to ensure domains remain accessible
- **Content Quality**: Monitoring for changes in domain reliability or content quality
- **User Feedback**: Tracking citation quality and source appropriateness

### Domain Updates
New domains may be added based on:
1. **Professional Recognition**: Citations in major medical literature
2. **Authority Status**: Government designation or professional endorsement
3. **Evidence Quality**: Peer-review processes and editorial standards
4. **User Needs**: Healthcare provider feedback and requirements

## Usage by Assistant Mode

### Patient Assistant (119 domains)
- **Focus**: Patient education and general health information
- **Sources**: Government agencies, major medical centers, patient education sites
- **Language**: Consumer-friendly medical information
- **Scope**: Basic medical concepts, symptoms, general treatment information

### Provider Assistant (169 domains)
- **Focus**: Clinical decision support and professional medical information
- **Sources**: Medical journals, clinical databases, specialty organizations
- **Language**: Technical medical terminology and clinical details
- **Scope**: Diagnostic criteria, treatment protocols, drug information, clinical guidelines

## Geographic Prioritization

### Canadian Users
1. **Primary**: Canadian federal and provincial health authorities
2. **Secondary**: Canadian medical organizations and hospitals
3. **Tertiary**: U.S. and international sources

### International Users
1. **Primary**: WHO, major international health organizations
2. **Secondary**: U.S. federal health agencies (CDC, NIH, FDA)
3. **Tertiary**: UK (NHS), European (EMA), and other national authorities

## Security Considerations

### Domain Verification
- **HTTPS Requirement**: All domains must support secure HTTPS connections
- **Certificate Validation**: SSL certificate verification for all requests
- **Request Limits**: Rate limiting on web_fetch requests per session

### Content Safety
- **Medical Focus**: Domains selected specifically for medical information quality
- **Professional Standards**: Sources maintain editorial and peer-review standards
- **No Commercial Bias**: Exclusion of domains with primary commercial intent

## Troubleshooting

### Common Issues

#### Citation from Unlisted Domain
If users notice citations from domains not in the trusted list:
1. **Check Deduplication**: Ensure provider domains are properly merged
2. **Verify Subdomains**: Some sites use multiple subdomains
3. **Review Logs**: Check web_fetch logs for unexpected domain requests

#### Missing Expected Sources
If expected medical sources are missing:
1. **Domain Variants**: Check for www vs non-www versions
2. **Subdomain Issues**: Some sites use medical-specific subdomains
3. **Recent Changes**: Sites may have changed domains or structure

#### Access Failures
If domains become inaccessible:
1. **Temporary Outages**: Sites may be temporarily unavailable
2. **Domain Changes**: Organizations may have changed their web presence
3. **Geographic Restrictions**: Some sites may restrict access by region

## Future Enhancements

### Planned Improvements
1. **Dynamic Domain Scoring**: Quality scoring based on citation frequency and user feedback
2. **Geographic Expansion**: Additional regional health authorities
3. **Specialty Domains**: Disease-specific and specialty organization expansion
4. **Real-time Validation**: Automated domain accessibility checking
5. **Citation Analytics**: Tracking most-used and highest-quality sources

### Evaluation Metrics
- **Citation Quality**: User and provider feedback on source appropriateness
- **Domain Coverage**: Percentage of queries successfully answered with trusted sources
- **Access Reliability**: Uptime and accessibility monitoring for all domains
- **Content Currency**: Tracking publication dates and content freshness