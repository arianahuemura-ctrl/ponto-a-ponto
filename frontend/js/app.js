$('load').addEventListener('click', loadNearby);
$('reset').addEventListener('click', resetSelection);
$('address-form').addEventListener('submit', searchAddress);
addEventListener('keydown', handleSelectionKeydown);

let legendModalHistoryPushed = false;
const legendModal = $('legend-modal');

function hideLegendModal() {
	legendModal.hidden = true;
	$('legend-toggle').setAttribute('aria-expanded', 'false');
	document.body.classList.remove('modal-open');
}

function openLegendModal() {
	legendModal.hidden = false;
	$('legend-toggle').setAttribute('aria-expanded', 'true');
	document.body.classList.add('modal-open');
	$('legend-close').focus();
	if (!legendModalHistoryPushed) {
		history.pushState({legendModal: true}, '', '#legenda');
		legendModalHistoryPushed = true;
	}
}

function closeLegendModal() {
	if (legendModal.hidden) return;
	hideLegendModal();
	if (legendModalHistoryPushed) {
		legendModalHistoryPushed = false;
		history.back();
	}
}

$('legend-toggle').addEventListener('click', openLegendModal);
$('legend-close').addEventListener('click', closeLegendModal);
$('legend-modal').addEventListener('click', event => {
	if (event.target.matches('[data-close-legend]')) closeLegendModal();
});
addEventListener('popstate', () => {
	if (!legendModal.hidden) {
		legendModalHistoryPushed = false;
		hideLegendModal();
	}
});
addEventListener('keydown', event => {
	if (event.key === 'Escape' && !legendModal.hidden) closeLegendModal();
});