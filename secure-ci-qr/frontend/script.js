document.addEventListener('DOMContentLoaded', () => {
    const textInput = document.getElementById('text-input');
    const generateBtn = document.getElementById('generate-btn');
    const btnText = generateBtn.querySelector('span');
    const spinner = generateBtn.querySelector('.spinner');
    const qrPlaceholder = document.getElementById('qr-placeholder');
    const qrImage = document.getElementById('qr-image');
    const downloadBtn = document.getElementById('download-btn');
    const errorMessage = document.getElementById('error-message');

    let currentObjectUrl = null;

    generateBtn.addEventListener('click', generateQR);
    textInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') generateQR();
    });

    async function pollStatus(taskId) {
        return new Promise((resolve, reject) => {
            const interval = setInterval(async () => {
                try {
                    const res = await fetch(`/api/status/${taskId}`);
                    if (!res.ok) {
                        const errorData = await res.json();
                        clearInterval(interval);
                        reject(new Error(errorData.error || 'Task failed'));
                        return;
                    }
                    const data = await res.json();
                    if (data.status === 'SUCCESS') {
                        clearInterval(interval);
                        resolve(data.image_base64);
                    } else if (data.status === 'FAILURE') {
                        clearInterval(interval);
                        reject(new Error(data.error || 'Task failed'));
                    }
                    // else it is PENDING, keep polling
                } catch (e) {
                    clearInterval(interval);
                    reject(e);
                }
            }, 1000);
        });
    }

    async function generateQR() {
        const text = textInput.value.trim();
        
        if (!text) {
            showError("Please enter some text or a URL.");
            return;
        }

        hideError();
        setLoading(true);

        try {
            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to start generation task');
            }

            const taskData = await response.json();
            const taskId = taskData.task_id;

            // Poll the status
            const base64Image = await pollStatus(taskId);
            
            qrImage.src = 'data:image/png;base64,' + base64Image;
            qrImage.classList.remove('hidden');
            qrPlaceholder.classList.add('hidden');
            downloadBtn.classList.remove('hidden');

            downloadBtn.onclick = () => {
                const a = document.createElement('a');
                a.href = qrImage.src;
                a.download = 'qrcode.png';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            };

        } catch (error) {
            showError(error.message);
            qrImage.classList.add('hidden');
            qrPlaceholder.classList.remove('hidden');
            downloadBtn.classList.add('hidden');
        } finally {
            setLoading(false);
        }
    }

    function setLoading(isLoading) {
        if (isLoading) {
            generateBtn.disabled = true;
            btnText.classList.add('hidden');
            spinner.classList.remove('hidden');
        } else {
            generateBtn.disabled = false;
            btnText.classList.remove('hidden');
            spinner.classList.add('hidden');
        }
    }

    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.classList.remove('hidden');
    }

    function hideError() {
        errorMessage.classList.add('hidden');
    }
});
