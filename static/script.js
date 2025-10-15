document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const apiKeyInput = document.getElementById('api-key');
    const modelSelect = document.getElementById('model-select');
    const modelWarning = document.getElementById('model-warning');
    const promptInput = document.getElementById('prompt-input');
    const generateBtn = document.getElementById('generate-btn');
    
    const widthSlider = document.getElementById('width-slider');
    const widthValue = document.getElementById('width-value');
    const heightSlider = document.getElementById('height-slider');
    const heightValue = document.getElementById('height-value');
    const stepsSlider = document.getElementById('steps-slider');
    const stepsValue = document.getElementById('steps-value');
    const countSlider = document.getElementById('count-slider');
    const countValue = document.getElementById('count-value');

    const imageGrid = document.getElementById('image-grid');
    const spinner = document.getElementById('spinner');
    const errorMessage = document.getElementById('error-message');
    const placeholder = document.getElementById('placeholder');

    // --- Functions ---

    /**
     * Fetches models from the API and populates the dropdown.
     * Manages the disabled state of controls based on success or failure.
     */
    async function populateModels() {
        // 1. Reset and disable controls at the start
        modelSelect.innerHTML = '';
        modelSelect.disabled = true;
        generateBtn.disabled = true;
        hideError();

        const apiKey = apiKeyInput.value.trim();
        if (!apiKey) {
            const placeholderOption = document.createElement('option');
            placeholderOption.textContent = "请输入API Key以加载模型";
            modelSelect.appendChild(placeholderOption);
            return;
        }

        // 2. Show loading state in the dropdown
        const loadingOption = document.createElement('option');
        loadingOption.textContent = "正在加载模型...";
        modelSelect.appendChild(loadingOption);

        try {
            const response = await fetch('/v1/models', {
                headers: { 'Authorization': `Bearer ${apiKey}` }
            });
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.detail || '获取模型列表失败。');
            }
            
            // 3. On success, populate dropdown and enable controls
            modelSelect.innerHTML = ''; // Clear loading message
            result.data.forEach(model => {
                const option = document.createElement('option');
                option.value = model.id;
                option.textContent = model.id;
                modelSelect.appendChild(option);
            });
            
            modelSelect.disabled = false;
            generateBtn.disabled = false;
            handleModelChange(); // Show warning for the initially selected model if needed

        } catch (error) {
            // 4. On failure, show clear error messages
            showError(`模型加载失败: ${error.message}. 请检查您的 API Key.`);
            modelSelect.innerHTML = '';
            const errorOption = document.createElement('option');
            errorOption.textContent = "加载失败，请检查API Key";
            modelSelect.appendChild(errorOption);
        }
    }

    /**
     * Shows or hides the warning for the Flux-Krea model.
     */
    function handleModelChange() {
        const selectedModel = modelSelect.value;
        modelWarning.classList.toggle('hidden', selectedModel !== 'Flux-Krea');
    }

    /**
     * Handles the image generation request on button click.
     */
    async function handleGenerate() {
        const apiKey = apiKeyInput.value.trim();
        const prompt = promptInput.value.trim();
        const selectedModel = modelSelect.value;

        if (!apiKey || !prompt) {
            showError("请确保 API Key 和提示词都已填写。");
            return;
        }
        if (!selectedModel || modelSelect.disabled) {
            showError("模型未成功加载或未选择，请检查您的 API Key。");
            return;
        }

        setLoading(true);

        const payload = {
            model: selectedModel,
            prompt: prompt,
            n: parseInt(countSlider.value, 10),
            size: `${widthSlider.value}x${heightSlider.value}`,
            steps: parseInt(stepsSlider.value, 10),
            response_format: "b64_json"
        };

        try {
            const response = await fetch('/v1/images/generations', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${apiKey}`
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.detail || '生成失败，未知错误。');
            }

            if (result.data && result.data.length > 0) {
                displayImages(result.data);
            } else {
                throw new Error('API 返回了成功状态，但没有图片数据。');
            }
        } catch (error) {
            showError(error.message);
        } finally {
            setLoading(false);
        }
    }

    function displayImages(data) {
        imageGrid.innerHTML = '';
        data.forEach(item => {
            if (item.b64_json) {
                const imgContainer = document.createElement('div');
                imgContainer.className = 'image-container';
                const img = document.createElement('img');
                img.src = `data:image/png;base64,${item.b64_json}`;
                img.alt = 'Generated Image';
                imgContainer.appendChild(img);
                imageGrid.appendChild(imgContainer);
            }
        });
    }

    function setLoading(isLoading) {
        generateBtn.disabled = isLoading;
        spinner.classList.toggle('hidden', !isLoading);
        placeholder.classList.toggle('hidden', isLoading || imageGrid.children.length > 0);
        if (isLoading) {
            imageGrid.innerHTML = '';
            hideError();
        }
    }

    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.classList.remove('hidden');
        imageGrid.innerHTML = '';
        placeholder.classList.add('hidden');
    }

    function hideError() {
        errorMessage.classList.add('hidden');
    }

    // --- Event Listeners ---
    
    widthSlider.addEventListener('input', () => widthValue.textContent = `${widthSlider.value}px`);
    heightSlider.addEventListener('input', () => heightValue.textContent = `${heightSlider.value}px`);
    stepsSlider.addEventListener('input', () => stepsValue.textContent = stepsSlider.value);
    countSlider.addEventListener('input', () => countValue.textContent = countSlider.value);

    generateBtn.addEventListener('click', handleGenerate);
    modelSelect.addEventListener('change', handleModelChange);
    // When the user finishes editing the API key, try to populate models.
    apiKeyInput.addEventListener('change', populateModels);

    // --- Initial Load ---
    // Attempt to load models as soon as the page is ready.
    populateModels();
});
