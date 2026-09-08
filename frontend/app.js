async function processVideo() {
    const urlInput = document.getElementById('ytUrl').value;
    const btn = document.getElementById('generateBtn');
    const loading = document.getElementById('loading');
    const resultSection = document.getElementById('resultSection');
    const clipsGrid = document.getElementById('clipsGrid');

    if (!urlInput) {
        alert("Harap masukkan URL YouTube!");
        return;
    }

    btn.disabled = true;
    loading.classList.remove('hidden');
    resultSection.classList.add('hidden');
    clipsGrid.innerHTML = '';

    try {
        const response = await fetch('http://localhost:8000/api/generate-clips', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: urlInput })
        });

        const data = await response.json();

        if (data.status === 'success') {
            data.clips.forEach(clip => {
                const card = document.createElement('div');
                card.className = 'clip-card';
                card.innerHTML = `
                    <h3>${clip.title}</h3>
                    <p><strong>Alasan AI:</strong> ${clip.reason}</p>
                    <a href="http://localhost:8000${clip.download_url}" download target="_blank">Download MP4 (9:16)</a>
                `;
                clipsGrid.appendChild(card);
            });
            resultSection.classList.remove('hidden');
        } else {
            alert('Gagal memproses video.');
        }
    } catch (err) {
        console.error(err);
        alert('Terjadi kesalahan koneksi ke server Backend!');
    } finally {
        btn.disabled = false;
        loading.classList.add('hidden');
    }
}
