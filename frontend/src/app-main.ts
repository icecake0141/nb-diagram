import { initDiagram } from './diagram.js';
import { initImportWorkflow } from './import-workflow.js';

function bootstrap() {
  initImportWorkflow();
  initDiagram();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', bootstrap);
} else {
  bootstrap();
}
