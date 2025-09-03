// ts_parser.js
const ts = require("typescript");
const fs = require("fs");

function analyzeTypeScript(filePath) {
    const results = {
        functions: {},
        classes: {},
        imports: {}, // { 'module_path': {'original_name': 'alias_name'} }
        function_calls: {}, // { 'caller_func': ['called_func1', ...] }
        error: null,
    };

    let sourceFile;
    try {
        const sourceCode = fs.readFileSync(filePath, "utf8");
        sourceFile = ts.createSourceFile(
            filePath,
            sourceCode,
            ts.ScriptTarget.Latest,
            true
        );
    } catch (e) {
        results.error = `Could not read or parse file: ${e.message}`;
        return results;
    }

    let currentFunctionName = null;

    function visit(node) {
        // --- インポート宣言を解析 ---
        if (ts.isImportDeclaration(node)) {
            const modulePath = node.moduleSpecifier.getText(sourceFile).slice(1, -1); // クォートを削除
            results.imports[modulePath] = {};
            if (node.importClause) {
                // `import { func1 as f1, func2 } from './module'` のような名前付きインポート
                if (node.importClause.namedBindings && ts.isNamedImports(node.importClause.namedBindings)) {
                    node.importClause.namedBindings.elements.forEach(element => {
                        const originalName = element.propertyName ? element.propertyName.text : element.name.text;
                        const aliasName = element.name.text;
                        results.imports[modulePath][originalName] = aliasName;
                    });
                }
            }
        }

        // --- 関数定義を解析 ---
        if (ts.isFunctionDeclaration(node) && node.name) {
            const funcName = node.name.text;
            results.functions[funcName] = node.getText(sourceFile);
            results.function_calls[funcName] = [];
            
            const originalFunctionName = currentFunctionName;
            currentFunctionName = funcName;
            ts.forEachChild(node, visit); // 関数の中身を再帰的に探索
            currentFunctionName = originalFunctionName;
            return; // 子ノードは探索済みなのでここで終了
        }
        
        // --- クラス定義を解析 ---
        if (ts.isClassDeclaration(node) && node.name) {
            const className = node.name.text;
            results.classes[className] = node.getText(sourceFile);
            // (クラス内のメソッド解析もここに追加可能)
        }

        // --- 関数呼び出しを解析 ---
        if (ts.isCallExpression(node) && currentFunctionName) {
            const expression = node.expression;
            let calledFuncName = null;

            if (ts.isIdentifier(expression)) {
                // 例: myFunction()
                calledFuncName = expression.text;
            } else if (ts.isPropertyAccessExpression(expression)) {
                // 例: console.log(), myObj.method()
                calledFuncName = expression.name.text;
            }
            
            if (calledFuncName) {
                results.function_calls[currentFunctionName].push(calledFuncName);
            }
        }

        ts.forEachChild(node, visit);
    }

    visit(sourceFile);
    return results;
}

// --- メイン処理 ---
// コマンドライン引数からファイルパスを取得
const filePath = process.argv[2];
if (!filePath) {
    console.error(JSON.stringify({ error: "No file path provided." }));
    process.exit(1);
}

const analysisResult = analyzeTypeScript(filePath);
console.log(JSON.stringify(analysisResult, null, 2));