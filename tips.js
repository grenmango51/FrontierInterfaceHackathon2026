// Somatic tips for biofeedback challenge.
// suits tags: "high-hr" = user struggling, "near-success" = bar > 66%, "anytime" = always appropriate
const TIPS = [
    { text: "Soften your jaw.", suits: ["high-hr", "anytime"] },
    { text: "Let your shoulders drop.", suits: ["high-hr", "anytime"] },
    { text: "Feel the weight of your hands.", suits: ["anytime"] },
    { text: "Relax the space behind your eyes.", suits: ["high-hr", "anytime"] },
    { text: "Notice your feet touching the floor.", suits: ["anytime"] },
    { text: "Let your belly be soft.", suits: ["high-hr", "anytime"] },
    { text: "Feel the air fill the back of your ribs.", suits: ["anytime"] },
    { text: "Unclench your hands.", suits: ["high-hr", "anytime"] },
    { text: "Let your tongue fall from the roof of your mouth.", suits: ["high-hr", "anytime"] },
    { text: "Feel the ground holding you.", suits: ["anytime"] },
    { text: "Soften the muscles around your eyes.", suits: ["near-success", "anytime"] },
    { text: "Notice the pause at the end of each breath.", suits: ["near-success", "anytime"] },
    { text: "Let each exhale be longer than you think.", suits: ["anytime"] },
    { text: "Feel your heartbeat slow with each breath.", suits: ["near-success"] },
    { text: "Let your face be empty.", suits: ["high-hr", "anytime"] },
    { text: "Rest your gaze — soft, unfocused.", suits: ["anytime"] },
    { text: "Let the breath do the work.", suits: ["near-success", "anytime"] },
    { text: "Feel stillness gathering in your chest.", suits: ["near-success"] },
    { text: "Nothing to do. Only this breath.", suits: ["anytime"] },
    { text: "Let the exhale carry it all away.", suits: ["anytime"] },
];

// v1: ignores state, returns random tip
// v2: pass state bucket ('high-hr'|'near-success'|'anytime') to filter by suits
function pickNextTip(currentTip, state) {
    const pool = state
        ? TIPS.filter(t => t.suits.includes(state) || t.suits.includes('anytime'))
        : TIPS;
    const available = pool.filter(t => t.text !== currentTip);
    return available[Math.floor(Math.random() * available.length)].text;
}
