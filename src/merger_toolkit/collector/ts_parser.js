// ts_parser.js
const ts = require("typescript");
const fs = require("fs");

function analyzeTypeScript(filePath) {
    const results = {
        functions: {},
        function_locations: {},  // ★ 追加: 関数位置情報
        classes: {},
        imports: {}, // { 'module_path': {'original_name': 'alias_name'} }
        function_calls: {}, // { 'caller_func': [{'name': 'called_func', 'module': null}] }
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
    let currentClassName = null;  // ★ 追加: 現在のクラス名

    function getLineNumber(pos) {
        return sourceFile.getLineAndCharacterOfPosition(pos).line + 1;
    }

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
                // ★ 追加: デフォルトインポートの対応
                if (node.importClause.name) {
                    results.imports[modulePath]['default'] = node.importClause.name.text;
                }
            }
        }

        // --- クラス定義を解析 ---
        if (ts.isClassDeclaration(node) && node.name) {
            const className = node.name.text;
            results.classes[className] = node.getText(sourceFile);
            
            const originalClassName = currentClassName;
            currentClassName = className;
            ts.forEachChild(node, visit); // クラス内を探索
            currentClassName = originalClassName;
            return;
        }

        // --- 関数定義を解析 ---
        if (ts.isFunctionDeclaration(node) && node.name) {
            const funcName = node.name.text;
            const fullFuncName = currentClassName ? `${currentClassName}.${funcName}` : funcName;
            
            results.functions[fullFuncName] = node.getText(sourceFile);
            results.function_calls[fullFuncName] = [];
            
            // ★ 追加: 関数位置情報
            results.function_locations[fullFuncName] = {
                start: getLineNumber(node.getStart(sourceFile)),
                end: getLineNumber(node.getEnd()),
                class_name: currentClassName,
                function_name: funcName
            };
            
            const originalFunctionName = currentFunctionName;
            currentFunctionName = fullFuncName;
            ts.forEachChild(node, visit); // 関数の中身を再帰的に探索
            currentFunctionName = originalFunctionName;
            return; // 子ノードは探索済みなのでここで終了
        }
        
        // --- メソッド定義を解析 ---
        if (ts.isMethodDeclaration(node) && ts.isIdentifier(node.name)) {
            const funcName = node.name.text;
            const fullFuncName = currentClassName ? `${currentClassName}.${funcName}` : funcName;
            
            results.functions[fullFuncName] = node.getText(sourceFile);
            results.function_calls[fullFuncName] = [];
            
            // ★ 追加: メソッド位置情報
            results.function_locations[fullFuncName] = {
                start: getLineNumber(node.getStart(sourceFile)),
                end: getLineNumber(node.getEnd()),
                class_name: currentClassName,
                function_name: funcName
            };
            
            const originalFunctionName = currentFunctionName;
            currentFunctionName = fullFuncName;
            ts.forEachChild(node, visit); // メソッドの中身を再帰的に探索
            currentFunctionName = originalFunctionName;
            return;
        }

        // --- アロー関数の変数宣言を解析 ---
        if (ts.isVariableStatement(node)) {
            node.declarationList.declarations.forEach(declaration => {
                if (ts.isIdentifier(declaration.name) && declaration.initializer && 
                    (ts.isArrowFunction(declaration.initializer) || ts.isFunctionExpression(declaration.initializer))) {
                    
                    const funcName = declaration.name.text;
                    const fullFuncName = currentClassName ? `${currentClassName}.${funcName}` : funcName;
                    
                    results.functions[fullFuncName] = declaration.initializer.getText(sourceFile);
                    results.function_calls[fullFuncName] = [];
                    
                    // ★ 追加: アロー関数位置情報
                    results.function_locations[fullFuncName] = {
                        start: getLineNumber(declaration.initializer.getStart(sourceFile)),
                        end: getLineNumber(declaration.initializer.getEnd()),
                        class_name: currentClassName,
                        function_name: funcName
                    };
                    
                    const originalFunctionName = currentFunctionName;
                    currentFunctionName = fullFuncName;
                    ts.forEachChild(declaration.initializer, visit);
                    currentFunctionName = originalFunctionName;
                }
            });
        }

        // --- 関数呼び出しを解析 ---
        if (ts.isCallExpression(node) && currentFunctionName) {
            const expression = node.expression;
            let calledFuncName = null;
            let moduleName = null;

            if (ts.isIdentifier(expression)) {
                // 例: myFunction()
                calledFuncName = expression.text;
            } else if (ts.isPropertyAccessExpression(expression)) {
                // 例: console.log(), myObj.method()
                calledFuncName = expression.name.text;
                if (ts.isIdentifier(expression.expression)) {
                    moduleName = expression.expression.text;
                }
            }
            
            if (calledFuncName) {
                results.function_calls[currentFunctionName].push({
                    name: calledFuncName,
                    module: moduleName
                });
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
