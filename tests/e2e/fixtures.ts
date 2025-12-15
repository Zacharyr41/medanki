import { test as base, expect } from '@playwright/test'
import * as fs from 'fs'
import * as path from 'path'
import * as os from 'os'
import { config } from './config'

interface TestFixtures {
  samplePdfPath: string
  sampleMdPath: string
  sampleDocxPath: string
  largeMdPath: string
  invalidFilePath: string
  tempDir: string
  apiBaseUrl: string
  webBaseUrl: string
}

export const test = base.extend<TestFixtures>({
  tempDir: async ({}, use) => {
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'medanki-e2e-'))
    await use(tempDir)
    fs.rmSync(tempDir, { recursive: true, force: true })
  },

  samplePdfPath: async ({ tempDir }, use) => {
    const pdfPath = path.join(tempDir, 'sample.pdf')
    const pdfContent = Buffer.from([
      0x25, 0x50, 0x44, 0x46, 0x2d, 0x31, 0x2e, 0x34, 0x0a,
      0x31, 0x20, 0x30, 0x20, 0x6f, 0x62, 0x6a, 0x0a,
      0x3c, 0x3c, 0x20, 0x2f, 0x54, 0x79, 0x70, 0x65, 0x20, 0x2f, 0x43, 0x61, 0x74, 0x61, 0x6c, 0x6f, 0x67, 0x0a,
      0x2f, 0x50, 0x61, 0x67, 0x65, 0x73, 0x20, 0x32, 0x20, 0x30, 0x20, 0x52, 0x0a,
      0x3e, 0x3e, 0x0a,
      0x65, 0x6e, 0x64, 0x6f, 0x62, 0x6a, 0x0a,
      0x32, 0x20, 0x30, 0x20, 0x6f, 0x62, 0x6a, 0x0a,
      0x3c, 0x3c, 0x20, 0x2f, 0x54, 0x79, 0x70, 0x65, 0x20, 0x2f, 0x50, 0x61, 0x67, 0x65, 0x73, 0x0a,
      0x2f, 0x4b, 0x69, 0x64, 0x73, 0x20, 0x5b, 0x33, 0x20, 0x30, 0x20, 0x52, 0x5d, 0x0a,
      0x2f, 0x43, 0x6f, 0x75, 0x6e, 0x74, 0x20, 0x31, 0x0a,
      0x3e, 0x3e, 0x0a,
      0x65, 0x6e, 0x64, 0x6f, 0x62, 0x6a, 0x0a,
      0x33, 0x20, 0x30, 0x20, 0x6f, 0x62, 0x6a, 0x0a,
      0x3c, 0x3c, 0x20, 0x2f, 0x54, 0x79, 0x70, 0x65, 0x20, 0x2f, 0x50, 0x61, 0x67, 0x65, 0x0a,
      0x2f, 0x50, 0x61, 0x72, 0x65, 0x6e, 0x74, 0x20, 0x32, 0x20, 0x30, 0x20, 0x52, 0x0a,
      0x2f, 0x4d, 0x65, 0x64, 0x69, 0x61, 0x42, 0x6f, 0x78, 0x20, 0x5b, 0x30, 0x20, 0x30, 0x20, 0x36, 0x31, 0x32, 0x20, 0x37, 0x39, 0x32, 0x5d, 0x0a,
      0x3e, 0x3e, 0x0a,
      0x65, 0x6e, 0x64, 0x6f, 0x62, 0x6a, 0x0a,
      0x78, 0x72, 0x65, 0x66, 0x0a,
      0x30, 0x20, 0x34, 0x0a,
      0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x20, 0x36, 0x35, 0x35, 0x33, 0x35, 0x20, 0x66, 0x0a,
      0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x39, 0x20, 0x30, 0x30, 0x30, 0x30, 0x30, 0x20, 0x6e, 0x0a,
      0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x35, 0x38, 0x20, 0x30, 0x30, 0x30, 0x30, 0x30, 0x20, 0x6e, 0x0a,
      0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x31, 0x31, 0x35, 0x20, 0x30, 0x30, 0x30, 0x30, 0x30, 0x20, 0x6e, 0x0a,
      0x74, 0x72, 0x61, 0x69, 0x6c, 0x65, 0x72, 0x0a,
      0x3c, 0x3c, 0x20, 0x2f, 0x53, 0x69, 0x7a, 0x65, 0x20, 0x34, 0x0a,
      0x2f, 0x52, 0x6f, 0x6f, 0x74, 0x20, 0x31, 0x20, 0x30, 0x20, 0x52, 0x0a,
      0x3e, 0x3e, 0x0a,
      0x73, 0x74, 0x61, 0x72, 0x74, 0x78, 0x72, 0x65, 0x66, 0x0a,
      0x32, 0x30, 0x34, 0x0a,
      0x25, 0x25, 0x45, 0x4f, 0x46, 0x0a,
    ])
    fs.writeFileSync(pdfPath, pdfContent)
    await use(pdfPath)
  },

  sampleMdPath: async ({ tempDir }, use) => {
    const mdPath = path.join(tempDir, 'sample.md')
    const mdContent = `# Medical Cardiology Notes

## Acute Coronary Syndrome

Acute coronary syndrome (ACS) encompasses a spectrum of conditions including:
- Unstable angina
- NSTEMI (Non-ST-elevation myocardial infarction)
- STEMI (ST-elevation myocardial infarction)

### Pathophysiology
The primary mechanism is atherosclerotic plaque rupture leading to:
1. Platelet aggregation
2. Thrombus formation
3. Coronary artery occlusion

### Clinical Presentation
Patients typically present with:
- Substernal chest pain radiating to the left arm
- Diaphoresis
- Shortness of breath
- Nausea/vomiting

### Management
Initial treatment includes:
- Aspirin 325mg
- Heparin anticoagulation
- Beta-blockers
- ACE inhibitors
`
    fs.writeFileSync(mdPath, mdContent)
    await use(mdPath)
  },

  sampleDocxPath: async ({ tempDir }, use) => {
    const docxPath = path.join(tempDir, 'sample.docx')
    const docxContent = Buffer.from([
      0x50, 0x4b, 0x03, 0x04, 0x14, 0x00, 0x00, 0x00, 0x08, 0x00,
      0x00, 0x00, 0x21, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    ])
    fs.writeFileSync(docxPath, docxContent)
    await use(docxPath)
  },

  largeMdPath: async ({ tempDir }, use) => {
    const mdPath = path.join(tempDir, 'large.md')
    const sections = [
      '# Comprehensive Medical Review\n\n',
      '## Cardiovascular System\n\n',
      'The cardiovascular system consists of the heart, blood vessels, and blood. ' +
        'The heart is a muscular organ that pumps blood through the circulatory system. ' +
        'Blood carries oxygen and nutrients to tissues and removes carbon dioxide and waste products.\n\n',
      '### Heart Anatomy\n\n',
      'The heart has four chambers: the right atrium, right ventricle, left atrium, and left ventricle. ' +
        'The right side of the heart receives deoxygenated blood from the body and pumps it to the lungs. ' +
        'The left side receives oxygenated blood from the lungs and pumps it to the body.\n\n',
      '### Cardiac Cycle\n\n',
      'The cardiac cycle consists of systole (contraction) and diastole (relaxation). ' +
        'During systole, the ventricles contract and eject blood. During diastole, the ventricles relax and fill with blood. ' +
        'The sinoatrial node initiates each heartbeat as the natural pacemaker.\n\n',
      '## Respiratory System\n\n',
      'The respiratory system facilitates gas exchange between the body and the environment. ' +
        'Air enters through the nose or mouth, travels through the pharynx, larynx, trachea, bronchi, and bronchioles to reach the alveoli. ' +
        'Oxygen diffuses from alveoli into pulmonary capillaries while carbon dioxide diffuses in the opposite direction.\n\n',
      '### Lung Volumes\n\n',
      'Tidal volume is the amount of air inhaled or exhaled during normal breathing (~500mL). ' +
        'Vital capacity is the maximum amount of air that can be exhaled after maximum inhalation. ' +
        'Residual volume is the air remaining in lungs after maximum exhalation.\n\n',
      '## Renal System\n\n',
      'The kidneys filter blood, regulate fluid balance, and maintain electrolyte homeostasis. ' +
        'Each kidney contains approximately one million nephrons, the functional units of the kidney. ' +
        'The nephron consists of the glomerulus, proximal tubule, loop of Henle, distal tubule, and collecting duct.\n\n',
      '### Glomerular Filtration\n\n',
      'Blood enters the glomerulus through the afferent arteriole and exits through the efferent arteriole. ' +
        'Filtration occurs based on size and charge of molecules. ' +
        'The glomerular filtration rate (GFR) is approximately 125 mL/min or 180 L/day.\n\n',
    ]
    fs.writeFileSync(mdPath, sections.join(''))
    await use(mdPath)
  },

  invalidFilePath: async ({ tempDir }, use) => {
    const invalidPath = path.join(tempDir, 'invalid.xyz')
    fs.writeFileSync(invalidPath, 'This is not a valid medical document format')
    await use(invalidPath)
  },

  apiBaseUrl: async ({}, use) => {
    await use(config.apiUrl)
  },

  webBaseUrl: async ({}, use) => {
    await use(config.baseUrl)
  },
})

export { expect }
