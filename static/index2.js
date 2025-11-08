	< !--document.addEventListener('DOMContentLoaded', () => {
		-->
	< !---->
	< !-- 		// NOTE: This is for the WHO ECT -->
	< !---->
	< !-- 		const mySettings = { -- >
	< !--apiServerUrl: "https://id.who.int", -->
	< !--apiSecured: true, -->
	< !--popupMode: true, -->
	< !--searchByCodeOrURI: true, -->
	< !--flexisearchAvailable: true -- >
	< !-- 		}; -->
	< !---->
	< !---->
	< !-- 		const myCallbacks = { -- >
	< !---->
	< !--getNewTokenFunction: async () => {
	-->
	< !-- 				const url = "/api/newToken"; -->
	< !-- 				try {
		-->
	< !-- 					const response = await fetch(url); -->
	< !-- 					const result = await response.json(); -->
	< !-- 					return result.token; -->
	< !-- 				} catch (e) {
		-->
	< !--console.log("Error during the request", e); -->
	< !-- 					return null; -->
	< !-- 				} -->
	< !-- 			}, -->
	< !---->
	< !--selectedEntityFunction: (selectedEntity, ctwObject) => {
	-->
	< !-- 				// document.getElementById('icdCode').value = `${selectedEntity.code} - ${selectedEntity.title}`; -->
	< !---->
	< !-- 				if (selectedEntity.iNo == 1) {
		-->
	< !--ECT.Handler.clear("1"); -->
	< !--document.getElementById('icdCode').value = `${selectedEntity.code} , ${selectedEntity.title}`; -->
	< !-- 				} -->
	< !-- 				else {
		-->
	< !--ECT.Handler.clear("2"); -->
	< !--document.getElementById('icdCode2').value = `${selectedEntity.code} , ${selectedEntity.title}`; -->
	< !--submitButton2.disabled = false; // Enable submit button -->
	< !-- 				} -->
	< !-- 			} -->
	< !-- 		}; -->
	< !---->
	< !---->
	< !--ECT.Handler.configure(mySettings, myCallbacks); -->
	< !-- 		// =============================================================== -->
	< !-- 		// NAMC-to-ICD Converter Logic -->
	< !-- 		// =============================================================== -->
	< !-- 		const searchInput = document.getElementById('search-input'); -->
	< !-- 		const suggestionsList = document.getElementById('suggestions'); -->
	< !-- 		const submitButton = document.getElementById('submit-button'); -->
	< !-- 		const icdCodeInput = document.getElementById('icdCode'); -->
	< !--let selectedNAMCTerm = ''; // Store the selected NAMC term (code, display, definition) -->
	< !---->
	< !-- 		// Autocomplete for NAMC search -->
	< !-- 		if (searchInput && suggestionsList) {
	-->
	< !--searchInput.addEventListener('input', async () => {
		-->
	< !-- 				const query = searchInput.value.trim(); -->
	< !-- 				if (query.length < 2) {
			-->
	< !--suggestionsList.innerHTML = ''; -->
	< !--suggestionsList.style.display = 'none'; -->
	< !--submitButton.disabled = true; -->
	< !--selectedNAMCTerm = ''; // Clear selected term if input is cleared -->
	< !-- 					return; -->
	< !-- 				} -->
	< !---->
	< !-- 				try {
			-->
	< !-- 					const response = await fetch(`/api/suggestions?q=${encodeURIComponent(query)}`); -->
	< !-- 					const data = await response.json(); -->
	< !--console.log(data); -->
	< !--displaySuggestions(data, suggestionsList); -->
	< !-- 				} catch (error) {
			-->
	< !--console.error('Error fetching suggestions:', error); -->
	< !-- 				} -->
	< !-- 			}); -->
	< !---->
	< !--suggestionsList.addEventListener('click', (event) => {
				-->
	< !-- 				if (event.target.classList.contains('suggestion-item')) {
					-->
	< !-- 					const [code, display, definition] = event.target.dataset.value.split('||'); // Split stored data -->
	< !--searchInput.value = display; // Show user-friendly display in input -->
	< !--selectedNAMCTerm = `${code},${display}`; // Store full term for submission -->
	< !--suggestionsList.innerHTML = ''; -->
	< !--suggestionsList.style.display = 'none'; -->
	< !--submitButton.disabled = false; // Enable convert button -->
	< !-- 				} -->
	< !-- 			}); -->
	< !---->
	< !-- 			// Hide suggestions when clicking outside -->
	< !--document.addEventListener('click', (event) => {
						-->
	< !-- 				if (!searchInput.contains(event.target) && !suggestionsList.contains(event.target)) {
							-->
	< !--suggestionsList.style.display = 'none'; -->
	< !-- 				} -->
	< !-- 			}); -->
	< !-- 		} -->
	< !---->
	< !-- 		// NAMC to ICD conversion -->
	< !-- 		if (submitButton) {
	-->
	< !--submitButton.addEventListener('click', async () => {
		-->
	< !-- 				if (!selectedNAMCTerm) {
			-->
	< !--alert('Please select a NAMC term from the suggestions.'); -->
	< !-- 					return; -->
	< !-- 				} -->
	< !---->
	< !--submitButton.disabled = true; // Disable to prevent multiple submissions -->
	< !--icdCodeInput.value = 'Converting...'; // Provide feedback -->
	< !---->
	< !-- 				try {
			-->
	< !---->
	< !-- 					const term = -->
	< !--ECT.Handler.search("1",) -->
	< !---->
	< !---->
	< !-- 					if (!response.ok) {
				-->
	< !-- 						throw new Error(`HTTP error! status: ${response.status}`); -->
	< !-- 					} -->
	< !---->
	< !-- 					const data = await response.json(); -->
	< !---->
	< !-- 					if (data && data.length > 0) {
				-->
	< !-- 						// Directly populate the ICD-11 input -->
	< !-- 						const icdCode = data[0][0]; -->
	< !-- 						const icdDisplay = data[0][1]; -->
	< !--icdCodeInput.value = `${icdCode},${icdDisplay}`; -->
	< !-- 						// Programmatically trigger the ICD-11 ECT to show details -->
	< !-- 						if (window.WHO && window.WHO.EmbeddedCodeTool) {
					-->
	< !-- 							// For ECT, it often responds to `change` or expects value to be set, -->
	< !-- 							// then an internal update. Setting directly works if ECT watches input. -->
	< !-- 							// If not, we might need a specific ECT method if available. -->
	< !-- 							// A simple way to ensure ECT updates is to clear and set again. -->
	< !-- 							// Let's try simulating input for robustness -->
	< !-- 							const originalValue = icdCodeInput.value; -->
	< !--icdCodeInput.value = ''; // Clear briefly -->
	< !--icdCodeInput.dispatchEvent(new Event('input', { bubbles: true })); // Simulate input event -->
	< !--icdCodeInput.value = `${icdCode},${icdDisplay}`; // Set the final value -->
	< !--icdCodeInput.dispatchEvent(new Event('input', { bubbles: true })); // Trigger another input event -->
	< !-- 						} -->
	< !-- 					} else {
				-->
	< !--icdCodeInput.value = 'No ICD-11 equivalent found.'; -->
	< !-- 					} -->
	< !-- 				} catch (error) {
			-->
	< !--console.error('Error during NAMC to ICD conversion:', error); -->
	< !--icdCodeInput.value = 'Error during conversion.'; -->
	< !-- 				} finally {
			-->
	< !--submitButton.disabled = false; // Re-enable button -->
	< !-- 				} -->
	< !-- 			}); -->
	< !-- 		} -->
	< !---->
	< !-- 		// =============================================================== -->
	< !-- 		// ICD-to-NAMC Converter Logic -->
	< !-- 		// =============================================================== -->
	< !-- 		const icdCodeInput2 = document.getElementById('icdCode2'); -->
	< !-- 		const submitButton2 = document.getElementById('submit-button2'); -->
	< !-- 		const searchInput2 = document.getElementById('search-input2'); // This is the output field for NAMC -->
	< !-- 		const suggestionsList2 = document.getElementById('suggestions2'); // This can be used for secondary matches, if any -->
	< !---->
	< !-- 		// Enable/disable submit button for ICD-to-NAMC based on input -->
	< !-- 		if (icdCodeInput2 && submitButton2) {
	-->
	< !--icdCodeInput2.addEventListener('input', () => {
		-->
	< !--submitButton2.disabled = icdCodeInput2.value.trim().length < 2; -->
	< !-- 			}); -->
	< !-- 		} -->
	< !---->
	< !-- 		// ICD to NAMC conversion -->
	< !-- 		if (submitButton2) {
	-->
	< !--submitButton2.addEventListener('click', async () => {
		-->
	< !-- 				const query = icdCodeInput2.value.trim(); -->
	< !-- 				if (!query) {
			-->
	< !--alert('Please enter an ICD-11 term or code.'); -->
	< !-- 					return; -->
	< !-- 				} -->
	< !---->
	< !--submitButton2.disabled = true; // Disable to prevent multiple submissions -->
	< !--searchInput2.value = 'Converting...'; // Provide feedback -->
	< !--suggestionsList2.innerHTML = ''; // Clear previous NAMC results -->
	< !---->
	< !-- 				try {
			-->
	< !-- 					// The backend expects 'q' to contain the ICD term -->
	< !-- 					const response = await fetch(`/api/ICDtoNAMC?q=${encodeURIComponent(query)}`); -->
	< !---->
	< !-- 					if (!response.ok) {
				-->
	< !-- 						throw new Error(`HTTP error! status: ${response.status}`); -->
	< !-- 					} -->
	< !---->
	< !-- 					const data = await response.json(); -->
	< !-- 					if (data && data.length > 0) {
				-->
	< !-- 						const topResult = data[0]; -->
	< !-- 						// Populate the NAMC output field directly -->
	< !--searchInput2.value = `${topResult.term} (Code: ${topResult.code})`; -->
	< !---->
	< !-- 						// If there are more results, display them in the suggestions list -->
	< !-- 						if (data.length > 1) {
					-->
	< !--displayNAMCResultsInSuggestions(data.slice(1), suggestionsList2); -->
	< !-- 						} else {
					-->
	< !--suggestionsList2.style.display = 'none'; -->
	< !-- 						} -->
	< !---->
	< !-- 					} else {
				-->
	< !--searchInput2.value = 'No NAMC equivalent found.'; -->
	< !--suggestionsList2.style.display = 'none'; -->
	< !-- 					} -->
	< !---->
	< !-- 				} catch (error) {
			-->
	< !--console.error('Error during ICD to NAMC conversion:', error); -->
	< !--searchInput2.value = 'Error during conversion.'; -->
	< !-- 				} finally {
			-->
	< !--submitButton2.disabled = false; // Re-enable button -->
	< !-- 				} -->
	< !-- 			}); -->
	< !-- 		} -->
	< !---->
	< !-- 		// =================================== -->
	< !-- 		// Helper for displaying NAMC suggestions (secondary matches) -->
	< !-- 		// =================================== -->
	< !-- 		function displayNAMCResultsInSuggestions(results, targetList) {
		-->
	< !--targetList.innerHTML = ''; -->
	< !-- 			if (results.length === 0) {
			-->
	< !--targetList.style.display = 'none'; -->
	< !-- 				return; -->
	< !-- 			} -->
	< !--results.forEach(item => {
				-->
	< !-- 				const li = document.createElement('li'); -->
	< !--li.classList.add('suggestion-item', 'list-group-item'); -->
	< !--li.textContent = `${item.term} (Code: ${item.code}, Score: ${item.score.toFixed(0)}) - ${item.definition}`; -->
	< !--targetList.appendChild(li); -->
	< !-- 			}); -->
	< !--targetList.style.display = 'block'; -->
	< !-- 		} -->
	< !---->
	< !-- 		// Helper for displaying NAMC suggestions (primary search) -->
	< !-- 		function displaySuggestions(data, targetList) {
		-->
	< !--targetList.innerHTML = ''; -->
	< !-- 			if (data.length === 0) {
			-->
	< !--targetList.style.display = 'none'; -->
	< !-- 				return; -->
	< !-- 			} -->
	< !--data.forEach(item => {
				-->
	< !-- 				const li = document.createElement('li'); -->
	< !--li.classList.add('suggestion-item', 'list-group-item'); -->
	< !-- 				// Store all parts in a dataset attribute -->
	< !--li.dataset.value = `${item[0]}||${item[1]}||${item[2]}`; -->
	< !--li.textContent = item[1]; // Display the user-friendly name -->
	< !--targetList.appendChild(li); -->
	< !-- 			}); -->
	< !--targetList.style.display = 'block'; -->
	< !-- 		} -->
	< !---->
	< !---->
	< !-- 		// ==================================================================== -->
	< !-- 		// START: NLP CLINICAL NOTES SEARCH LOGIC (Works with the new main.py) -->
	< !-- 		// ==================================================================== -->
	< !-- 		const nlpSearchButton = document.getElementById('nlp-search-button'); -->
	< !-- 		const nlpSearchInput = document.getElementById('nlp-search-input'); -->
	< !-- 		const nlpResultsArea = document.getElementById('nlp-results-area'); -->
	< !-- 		const nlpSpinner = document.getElementById('nlp-search-spinner'); -->
	< !---->
	< !-- 		if (nlpSearchButton) {
	-->
	< !--nlpSearchButton.addEventListener('click', handleNLPSearch); -->
	< !-- 		} -->
	< !---->
	< !-- 		// Allow pressing Ctrl+Enter or Cmd+Enter to trigger the search -->
	< !-- 		if (nlpSearchInput) {
	-->
	< !--nlpSearchInput.addEventListener('keydown', (event) => {
		-->
	< !-- 				if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
			-->
	< !--event.preventDefault(); // Prevent new line in textarea -->
	< !--handleNLPSearch(); -->
	< !-- 				} -->
	< !-- 			}); -->
	< !-- 		} -->
	< !---->
	< !-- 		async function handleNLPSearch() {
		-->
	< !-- 			const query = nlpSearchInput.value.trim(); -->
	< !-- 			if (!query) {
			-->
	< !--alert('Please enter a clinical description to search.'); -->
	< !-- 				return; -->
	< !-- 			} -->
	< !---->
	< !-- 			// Show a loading state -->
	< !--nlpSpinner.classList.remove('d-none'); -->
	< !--nlpSearchButton.disabled = true; -->
	< !--nlpResultsArea.innerHTML = ''; // Clear previous results -->
	< !---->
	< !-- 			try {
			-->
	< !-- 				const response = await fetch('/api/nlp_search', { -- >
	< !--method: 'POST', -->
	< !--headers: { 'Content-Type': 'application/json' }, -->
	< !--body: JSON.stringify({ query: query }), -->
	< !-- 				}); -->
	< !---->
	< !-- 				if (!response.ok) {
			-->
	< !-- 					const errorData = await response.json(); -->
	< !-- 					throw new Error(errorData.error || `HTTP error! status: ${response.status}`); -->
	< !-- 				} -->
	< !---->
	< !-- 				const results = await response.json(); -->
	< !--displayNLPResults(results); -->
	< !---->
	< !-- 			} catch (error) {
	-->
	< !--console.error('NLP Search Error:', error); -->
	< !--nlpResultsArea.innerHTML = `<div class="alert alert-danger">An error occurred: ${error.message}</div>`; -->
	< !-- 			} finally {
	-->
	< !-- 				// Restore button to normal state -->
	< !--nlpSpinner.classList.add('d-none'); -->
	< !--nlpSearchButton.disabled = false; -->
	< !-- 			} -->
	< !-- 		} -->
	< !---->
	< !-- 		function displayNLPResults(results) {
		-->
	< !-- 			if (!results || results.length === 0) {
			-->
	< !--nlpResultsArea.innerHTML = '<div class="alert alert-warning text-center">No relevant terms found for the given description.</div>'; -->
	< !-- 				return; -->
	< !-- 			} -->
	< !---->
	< !-- 			// Map system names to Bootstrap badge colors for clear visual distinction -->
	< !-- 			const systemColors = { -- >
	< !-- 				"Siddha": "bg-primary", -->
	< !-- 				"Ayurveda": "bg-success", -->
	< !-- 				"Unani": "bg-info" -- >
	< !-- 			}; -->
	< !---->
	< !-- 			const resultsHtml = results.map(item => {
				-->
	< !-- 				const badgeColor = systemColors[item.system] || 'bg-secondary'; -->
	< !-- 				// Remove the redundant term from the definition for cleaner display -->
	< !-- 				const cleanDefinition = item.full_definition.replace(item.display + ': ', ''); -->
	< !---->
	< !-- 				return ` -->
	<!-- 					<div class="card shadow-sm mb-3"> -->
	<!-- 						<div class="card-body"> -->
	<!-- 							<div class="d-flex justify-content-between align-items-start"> -->
	<!-- 								<h5 class="card-title mb-1">${item.display}</h5> -->
	<!-- 								<span class="badge ${badgeColor} fs-6">${item.system}</span> -->
	<!-- 							</div> -->
	<!-- 							<h6 class="card-subtitle mb-2 text-muted">Code: ${item.code}</h6> -->
	<!-- 							<p class="card-text small mt-2">${cleanDefinition}</p> -->
	<!-- 						</div> -->
	<!-- 					</div> -->
	<!-- 				`; -->
	< !-- 			}).join(''); -->
	< !---->
	< !--nlpResultsArea.innerHTML = resultsHtml; -->
	< !-- 		} -->
	< !-- 		// =================================== -->
	< !-- 		// END: NLP CLINICAL NOTES SEARCH LOGIC -->
	< !-- 		// =================================== -->
	< !---->
	< !-- 	}); -->

