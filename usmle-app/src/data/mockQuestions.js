/**
 * Mock questions for testing the USMLE study app
 * Based on actual data schema with intentional artifacts for testing data cleaning
 */

export const mockQuestions = [
    {
        id: "EM-1-8",
        section: "Emergency Medicine",
        subsection: "CMS-1",
        questionNumber: 8,
        system: "Respiratory",
        questionStem: "A 13-year-old girl is brought to the emergency department 30 minutes after she fell off a sailboat into a freshwater lake. A witness reported that she was under water for approximately 2 minutes; when she was rescued, she was cyanotic and unresponsive. After initial mouth-to-mouth resuscitation, she began coughing and breathing again, and her color returned. On arrival in the emergency department, the patient is awake and alert. She has mild shortness of breath and a cough. Her temperature is 37°C (98.6°F), pulse is 108/min, respirations are 20/min, and blood pressure is 93/45 mm Hg. Pulse oximetry on room air shows an oxygen saturation of 94%. Auscultation of the lungs discloses mild wheezes. There are no signs of external trauma. A chest x-ray shows mild diffuse interstitial markings. Which of the following is the most appropriate next step in management?",
        choices: {
            A: "Admission to the hospital for observation",
            B: "Antibiotic therapy",
            C: "Corticosteroid therapy",
            D: "Diuretic therapy",
            E: "Noninvasive positive-pressure ventilation"
        },
        correctAnswer: "A",
        correctExplanation: "Admission to the hospital for observation is the most appropriate management for this young girl who recently suffered a nonfatal drowning incident. Unexpected submersion in water leads to reflexive breath holding followed by air hunger and an eventual reflexive inspiratory effort. This leads to hypoxia through either aspiration of water or laryngospasm when water contacts the vocal cords. Prolonged hypoxemia leads to end-organ dysfunction including acidosis, hypoxic brain injury, and cardiac arrhythmias. Exposure of the alveoli to water can lead to the development of acute respiratory distress syndrome (ARDS), which appears on chest imaging as noncardiogenic pulmonary edema. ARDS can develop immediately after injury or slowly over many hours and can be rapidly fatal. In general, all nonfatal drowning victims with any degree of hypoxia, respiratory distress, or infiltrates on imaging should be hospitalized to monitor for the evidence of the development of ARDS and complications of drowning.",
        incorrectExplanation: "nd E. Antibiotic therapy (Choice B) is not indicated in this patient. Antibiotics are reserved for patients with presumed or proven bacterial infections, but drowning does not necessarily predispose to the development of bacterial infection. Corticosteroid therapy (Choice C) is not useful in the management of drowning victims. It is more commonly used for shortness of breath in the setting of asthma, chronic obstructive pulmonary disease, and croup. Diuretic therapy (Choice D) is used to treat patients with hypervolemia that develops as a result of renal disease or decompensated heart failure, but diuretics are not useful in the treatment of drowning victims. r ~, ~ ~ r, Previous"
    },
    {
        id: "EM-1-6",
        section: "Emergency Medicine",
        subsection: "CMS-1",
        questionNumber: 6,
        system: "Neurological",
        questionStem: "A 47-year-old man is brought to the emergency department by a friend 30 minutes after a seizure. The friend says that while they were sitting on the couch at home, the patient suddenly became quiet, arched his back, and began to shake. The episode lasted 45 seconds. Immediately afterward, the patient was confused for 15 minutes. He has hypertension treated with amlodipine. He has no known drug allergies. He has smoked one pack of cigarettes daily for 20 years. He drinks eight to nine beers nightly. His last drink was 28 hours ago. On arrival, he is sleepy but responds to verbal stimuli. He appears restless. His temperature is 38.1°C (100.6°F), pulse is 106/min and regular, respirations are 18/min, and blood pressure is 148/92 mm Hg. Pulse oximetry on room air shows an oxygen saturation of 97%. Physical examination shows clammy skin. The remainder of the examination, including neurologic examination, shows no abnormalities. Which of the following is the most appropriate next step in management?",
        choices: {
            A: "Administration of dextrose and vitamin B1 (thiamine)",
            B: "Administration of lorazepam",
            C: "Administration of phenytoin",
            D: "CT scan of the head",
            E: "Intubation"
        },
        correctAnswer: "B",
        correctExplanation: "Alcohol increases the central nervous system activity of γ-aminobutyric acid (GABA), the main inhibitory neurotransmitter. Abrupt discontinuation of alcohol therefore leads to sympathetic (excitatory) excess. Uncomplicated alcohol withdrawal typically presents with tremors, anxiety, restlessness, headache, nausea, and diaphoresis, which can occur hours after the cessation of alcohol use. If left untreated, alcohol withdrawal can also be complicated by seizures and alcoholic hallucinosis (auditory or visual hallucinations). Delirium tremens, the most concerning and life-threatening complication of alcohol withdrawal, involves severe confusion and disorientation, fluctuations in consciousness, agitation, visual hallucinations, and autonomic instability (fluctuations in pulse and blood pressure with hyperthermia). Alcohol withdrawal is managed supportively with benzodiazepines (eg, lorazepam) to address agitation and prevent the symptoms of withdrawal, along with fluids, nutritional supplementation, and frequent assessment including vital sign checks.",
        incorrectExplanation: "nd E. Administration of dextrose and vitamin B1 (thiamine) (Choice A) may be helpful in this patient with chronic alcohol use disorder because of malnutrition, but it is more useful for treatment of Wernicke encephalopathy. This patient is presenting with alcohol withdrawal, making treatment with benzodiazepines more appropriate. Administration of phenytoin (Choice C) would be appropriate in cases of epilepsy, but this patient's seizure is likely provoked by alcohol withdrawal and should be treated with benzodiazepines. CT scan of the head (Choice D) would be appropriate in the evaluation of first-time unprovoked seizure. However, this patient's seizure - - - - - - - - - - - - - - - - - - - - - - - - - -- - - -- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - r ~, ~ ~ r, Previous"
    },
    {
        id: "EM-1-15",
        section: "Emergency Medicine",
        subsection: "CMS-1",
        questionNumber: 15,
        system: "Genitourinary",
        questionStem: "An otherwise healthy 18-year-old man is brought to the emergency department because of a 1-hour history of severe left testicular pain that began while he was walking his dog. He says he had a similar episode 1 week ago while he was jogging, but it resolved spontaneously within 30 minutes. He takes no medications. Vital signs are within normal limits. The abdomen is soft; there is tenderness of the left testis to palpation of the abdomen. There is erythema, mild edema, and severe tenderness to palpation of the left testis. Cremasteric reflex is absent on the left. The right testis appears normal. Which of the following is the most appropriate next step in management?",
        choices: {
            A: "CT scan of the scrotum",
            B: "Intramuscular administration of ceftriaxone and oral administration of azithromycin",
            C: "Intravenous administration of ketorolac",
            D: "Surgical consultation for orchiopexy",
            E: "Urinalysis"
        },
        correctAnswer: "D",
        correctExplanation: "Testicular torsion is caused by rotation of the testes around the spermatic cord. Compression of the blood vessel supply leads to edema, ischemia, and subsequent necrosis. It classically presents with acute testicular pain, tenderness to palpation, scrotal swelling, and a negative cremasteric reflex. The patient may also develop nausea and emesis and/or lower abdominal pain prior to the onset of scrotal pain. Physical examination may show a high-riding testis that is oriented transversely with surrounding erythema. Testicular torsion is typically a clinical diagnosis, although ultrasonography can be used for further evaluation if the diagnosis is unclear. Ultrasonography will demonstrate diminished or absent blood flow to the testes. Testicular torsion is a surgical emergency and requires surgical evaluation when the diagnosis is suspected. Surgery will allow for detorsion of the testes and orchiopexy (testicular fixation) of both testes to prevent recurrent torsion.",
        incorrectExplanation: "nd E. CT scan of the scrotum (Choice A) may demonstrate the torsion but is more costly and time-consuming than ultrasonography for evaluation. This patient has pathognomonic symptoms for testicular torsion, and surgical consultation is the most appropriate next step to prevent testicular necrosis. Intramuscular administration of ceftriaxone and oral administration of azithromycin (Choice B) would be appropriate therapy for the treatment of acute epididymitis caused by Neisseria gonorrhoeae or Chlamydia trachomatis. It commonly presents indolently, rather than acutely, with testicular pain, tenderness, and edema. However, cremasteric reflex will be present in acute epididymitis. Intravenous administration of ketorolac (Choice C) may improve this patient's pain. However, the more important initial step in management should be surgical consultation for detorsion and orchiopexy. Delays to surgical management increase the likelihood of - - - - - - - - - - - - - - - - - - - - r ~, ~ ~ r, Previous"
    },
    {
        id: "IM-2-12",
        section: "Internal Medicine",
        subsection: "CMS-2",
        questionNumber: 12,
        system: "Cardiovascular",
        questionStem: "A 65-year-old man comes to the physician because of a 3-month history of progressive dyspnea and fatigue. He has a history of hypertension and type 2 diabetes mellitus. His current medications include lisinopril, metformin, and aspirin. His temperature is 37°C (98.6°F), pulse is 88/min, respirations are 18/min, and blood pressure is 145/90 mm Hg. Physical examination shows jugular venous distention and bilateral lower extremity edema. Cardiac auscultation reveals an S3 gallop. Chest x-ray shows cardiomegaly and pulmonary vascular congestion. Echocardiography shows a left ventricular ejection fraction of 35%. Which of the following medications should be added to this patient's regimen?",
        choices: {
            A: "Amlodipine",
            B: "Carvedilol",
            C: "Digoxin",
            D: "Furosemide",
            E: "Hydralazine"
        },
        correctAnswer: "B",
        correctExplanation: "Beta-blockers such as carvedilol are indicated in patients with heart failure with reduced ejection fraction (HFrEF). These medications reduce sympathetic stimulation of the heart, decrease heart rate, and reduce myocardial oxygen demand. Clinical trials have demonstrated that beta-blockers reduce mortality and hospitalizations in patients with HFrEF. The patient should be started on a low dose and gradually titrated up to the target dose as tolerated. Other guideline-directed medical therapies for HFrEF include ACE inhibitors or ARBs, mineralocorticoid receptor antagonists, and SGLT2 inhibitors.",
        incorrectExplanation: "nd E. Amlodipine (Choice A) is a calcium channel blocker that is used for hypertension and angina. While it may help control blood pressure, it does not provide mortality benefit in heart failure. Digoxin (Choice C) can reduce hospitalizations in heart failure but does not reduce mortality. It is typically reserved for patients who remain symptomatic despite optimal therapy. Furosemide (Choice D) is a loop diuretic that helps relieve congestive symptoms but does not improve mortality. Hydralazine (Choice E) can be used in combination with nitrates in patients who cannot tolerate ACE inhibitors, but beta-blockers are preferred. - - - - - - - - - - - - - Previous"
    },
    {
        id: "IM-2-25",
        section: "Internal Medicine",
        subsection: "CMS-2",
        questionNumber: 25,
        system: "Endocrine",
        questionStem: "A 45-year-old woman comes to the physician for evaluation of fatigue and weight gain of 5 kg (11 lb) over the past 6 months. She also reports constipation and feeling cold all the time. Her menses have become irregular. Her temperature is 36.2°C (97.2°F), pulse is 58/min, respirations are 14/min, and blood pressure is 130/85 mm Hg. Physical examination shows dry skin, coarse hair, and delayed relaxation of deep tendon reflexes. Laboratory studies show a serum thyroid-stimulating hormone (TSH) concentration of 12 mU/L (normal: 0.5-5.0 mU/L). Which of the following is the most appropriate next step in management?",
        choices: {
            A: "Measurement of free T4",
            B: "Measurement of thyroid peroxidase antibodies",
            C: "Radioactive iodine uptake scan",
            D: "Thyroid ultrasonography",
            E: "Levothyroxine therapy"
        },
        correctAnswer: "A",
        correctExplanation: "When TSH is elevated, the next step is to measure free T4 to confirm the diagnosis and determine the severity of hypothyroidism. An elevated TSH with low free T4 confirms overt hypothyroidism, while elevated TSH with normal free T4 indicates subclinical hypothyroidism. The degree of T4 reduction helps guide the initial levothyroxine dose. Thyroid peroxidase antibodies can help determine the etiology but are not essential for initiating treatment.",
        incorrectExplanation: "nd E. Starting levothyroxine therapy (Choice E) without first confirming the diagnosis with free T4 measurement is premature. The free T4 level helps determine the severity and guides dosing. Thyroid peroxidase antibodies (Choice B) can identify Hashimoto thyroiditis but do not change immediate management. Radioactive iodine uptake scan (Choice C) is used to evaluate hyperthyroidism, not hypothyroidism. Thyroid ultrasonography (Choice D) is useful for evaluating nodules but is not needed for primary hypothyroidism evaluation. - - - - Previous Next Score Report Lab Values"
    }
];

/**
 * Get questions grouped by section and subsection for sidebar navigation
 */
export function getQuestionsBySection(questions) {
    const grouped = {};

    for (const question of questions) {
        const { section, subsection } = question;

        if (!grouped[section]) {
            grouped[section] = {};
        }

        if (!grouped[section][subsection]) {
            grouped[section][subsection] = [];
        }

        grouped[section][subsection].push(question);
    }

    return grouped;
}
