let uploadedFile = null;

// File upload handling
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFileSelect(files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileSelect(e.target.files[0]);
    }
});

function handleFileSelect(file) {
    const allowedTypes = ['application/pdf', 'application/vnd.ms-powerpoint', 
                         'application/vnd.openxmlformats-officedocument.presentationml.presentation'];
    
    if (!allowedTypes.includes(file.type)) {
        alert('サポートされていないファイル形式です。PPT、PPTX、PDFファイルを選択してください。');
        return;
    }
    
    if (file.size > 100 * 1024 * 1024) {
        alert('ファイルサイズが大きすぎます。100MB以下のファイルを選択してください。');
        return;
    }
    
    uploadedFile = file;
    document.getElementById('fileName').textContent = file.name;
    document.getElementById('fileInfo').style.display = 'flex';
    document.getElementById('uploadArea').style.display = 'none';
    document.getElementById('checkButton').disabled = false;
}

function removeFile() {
    uploadedFile = null;
    document.getElementById('fileInfo').style.display = 'none';
    document.getElementById('uploadArea').style.display = 'block';
    document.getElementById('checkButton').disabled = true;
    fileInput.value = '';
}

async function startFactCheck() {
    if (!uploadedFile) return;
    
    const apiKey = document.getElementById('apiKey').value;
    
    // Upload file
    const formData = new FormData();
    formData.append('file', uploadedFile);
    
    document.getElementById('loading').style.display = 'flex';
    
    try {
        const uploadResponse = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!uploadResponse.ok) {
            throw new Error('ファイルのアップロードに失敗しました');
        }
        
        const uploadData = await uploadResponse.json();
        
        // Start fact checking
        const checkResponse = await fetch(`/check/${uploadData.filename}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ api_key: apiKey })
        });
        
        if (!checkResponse.ok) {
            const error = await checkResponse.json();
            throw new Error(error.error || 'ファクトチェックに失敗しました');
        }
        
        const checkData = await checkResponse.json();
        displayResults(checkData);
        
    } catch (error) {
        alert(`エラー: ${error.message}`);
    } finally {
        document.getElementById('loading').style.display = 'none';
    }
}

function displayResults(data) {
    const resultsSection = document.getElementById('results');
    const summaryDiv = document.getElementById('resultsSummary');
    const detailDiv = document.getElementById('resultsDetail');
    const downloadDiv = document.getElementById('downloadLinks');
    
    // Display summary
    const report = data.report;
    summaryDiv.innerHTML = `
        <h3>チェック結果サマリー</h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-top: 15px;">
            <div>
                <div style="font-size: 24px; font-weight: bold;">${report.total_slides}</div>
                <div>総スライド数</div>
            </div>
            <div>
                <div style="font-size: 24px; font-weight: bold; color: #e74c3c;">${report.slides_with_issues}</div>
                <div>問題のあるスライド</div>
            </div>
            <div>
                <div style="font-size: 24px; font-weight: bold;">${report.total_issues}</div>
                <div>検出された問題</div>
            </div>
            <div>
                <div style="font-size: 24px; font-weight: bold;">$${report.total_cost_estimate.toFixed(4)}</div>
                <div>推定コスト</div>
            </div>
        </div>
    `;
    
    // Display detailed results
    detailDiv.innerHTML = '<h3>詳細結果</h3>';
    
    report.results.forEach(result => {
        if (result.issues && result.issues.length > 0) {
            const slideDiv = document.createElement('div');
            slideDiv.className = 'slide-result';
            
            let issuesHtml = `<h4>スライド ${result.slide_number}</h4>`;
            issuesHtml += `<p>${result.summary}</p>`;
            
            result.issues.forEach(issue => {
                issuesHtml += `
                    <div class="issue issue-${issue.severity}">
                        <strong>問題タイプ:</strong> ${issue.type}<br>
                        <strong>深刻度:</strong> ${issue.severity}<br>
                        <strong>該当テキスト:</strong> ${issue.original_text}<br>
                        <strong>説明:</strong> ${issue.issue_description}<br>
                        ${issue.correct_information ? `<strong>正しい情報:</strong> ${issue.correct_information}<br>` : ''}
                        <strong>信頼度:</strong> ${(issue.confidence * 100).toFixed(0)}%
                    </div>
                `;
            });
            
            slideDiv.innerHTML = issuesHtml;
            detailDiv.appendChild(slideDiv);
        }
    });
    
    // Display download links
    downloadDiv.innerHTML = '<h3>レポートをダウンロード</h3>';
    
    if (data.saved_files) {
        Object.entries(data.saved_files).forEach(([format, filepath]) => {
            const filename = filepath.split('/').pop();
            const link = document.createElement('a');
            link.href = `/download/${format}/${filename}`;
            link.textContent = format.toUpperCase() + 'でダウンロード';
            downloadDiv.appendChild(link);
        });
    }
    
    // Display improvement suggestions
    if (data.suggestions && data.suggestions.priority_fixes.length > 0) {
        const suggestionsDiv = document.createElement('div');
        suggestionsDiv.innerHTML = '<h3>優先的に修正すべき項目</h3>';
        
        data.suggestions.priority_fixes.forEach(fix => {
            suggestionsDiv.innerHTML += `
                <div style="padding: 10px; margin: 5px 0; background: #fff3cd; border-radius: 5px;">
                    <strong>スライド ${fix.slide}:</strong> ${fix.issue}
                </div>
            `;
        });
        
        detailDiv.appendChild(suggestionsDiv);
    }
    
    resultsSection.style.display = 'block';
}

async function quickCheck() {
    const text = document.getElementById('quickCheckText').value;
    if (!text.trim()) {
        alert('チェックするテキストを入力してください');
        return;
    }
    
    const apiKey = document.getElementById('apiKey').value;
    
    try {
        const response = await fetch('/quick-check', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ text, api_key: apiKey })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'クイックチェックに失敗しました');
        }
        
        const data = await response.json();
        displayQuickCheckResults(data.result);
        
    } catch (error) {
        alert(`エラー: ${error.message}`);
    }
}

function displayQuickCheckResults(result) {
    const resultsHtml = `
        <div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 5px;">
            <h4>クイックチェック結果</h4>
            <p>検出されたファクト: ${result.facts_found}件</p>
            <p>チェック済み: ${result.facts_checked}件</p>
            ${result.verification_results.map(vr => `
                <div style="margin: 10px 0; padding: 10px; background: white; border-radius: 5px;">
                    <strong>${vr.fact_text}</strong><br>
                    正確性: ${vr.is_correct ? '✓ 正しい' : '✗ 誤り'}<br>
                    ${vr.explanation || ''}
                </div>
            `).join('')}
        </div>
    `;
    
    document.getElementById('quickCheckText').insertAdjacentHTML('afterend', resultsHtml);
}

function showCostEstimate() {
    document.getElementById('costModal').style.display = 'block';
}

function closeCostModal() {
    document.getElementById('costModal').style.display = 'none';
}

async function calculateCost() {
    const slideCount = parseInt(document.getElementById('slideCount').value);
    const fileCount = parseInt(document.getElementById('fileCount').value);
    
    try {
        const response = await fetch('/cost-estimate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ slide_count: slideCount, file_count: fileCount })
        });
        
        const data = await response.json();
        
        document.getElementById('costResult').innerHTML = `
            <h4>推定コスト</h4>
            <p style="font-size: 24px; font-weight: bold;">$${data.estimated_cost.toFixed(4)}</p>
            <p>入力トークン: ${data.input_tokens.toLocaleString()}</p>
            <p>出力トークン: ${data.output_tokens.toLocaleString()}</p>
            <hr>
            <p>内訳:</p>
            <p>入力コスト: $${data.cost_breakdown.input_cost.toFixed(4)}</p>
            <p>出力コスト: $${data.cost_breakdown.output_cost.toFixed(4)}</p>
        `;
        
    } catch (error) {
        alert('コスト計算に失敗しました');
    }
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('costModal');
    if (event.target == modal) {
        modal.style.display = 'none';
    }
}