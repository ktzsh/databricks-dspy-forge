import React, { useState } from 'react';
import { X, Plus, Trash2, Zap } from 'lucide-react';

interface ScoringFunction {
  id: string;
  type: 'Correctness' | 'Guidelines';
  name: string;
  guideline?: string;
  weightage: number;
}

interface OptimizerConfig {
  [key: string]: string;
}

interface FormErrors {
  [key: string]: string;
}

interface OptimizeModalProps {
  workflowId: string | null;
  workflowIR: { nodes: any[], edges: any[] } | null;
  onClose: () => void;
  onOptimizationStart?: (optimizationId: string) => void;
  isOptimizationActive?: boolean;
}

const OptimizerTypes = ['GEPA', 'BootstrapFewShotWithRandomSearch', 'MIPROv2'] as const;
type OptimizerType = typeof OptimizerTypes[number];

// Default configurations for each optimizer
const DEFAULT_OPTIMIZER_CONFIGS: Record<OptimizerType, OptimizerConfig> = {
  'BootstrapFewShotWithRandomSearch': {
    'max_rounds': '1',
    'max_bootstrapped_demos': '4',
    'max_labeled_demos': '16',
    'num_candidate_programs': '16',
  },
  'GEPA': {
    'auto': 'light',
    'reflection_lm': 'databricks-claude-3-7-sonnet'
  },
  'MIPROv2': {
    'num_candidates': '10',
    'init_temperature': '0.7'
  }
};

const OptimizeModal: React.FC<OptimizeModalProps> = ({
  workflowId,
  workflowIR,
  onClose,
  onOptimizationStart,
  isOptimizationActive = false
}) => {
  const [optimizerName, setOptimizerName] = useState<OptimizerType>('BootstrapFewShotWithRandomSearch');
  const [optimizerConfig, setOptimizerConfig] = useState<OptimizerConfig>(
    DEFAULT_OPTIMIZER_CONFIGS['BootstrapFewShotWithRandomSearch']
  );
  const [scoringFunctions, setScoringFunctions] = useState<ScoringFunction[]>([
    { id: '1', type: 'Correctness', name: 'Correctness', weightage: 100 }
  ]);

  // Training and validation dataset config
  const [trainCatalog, setTrainCatalog] = useState('');
  const [trainSchema, setTrainSchema] = useState('');
  const [trainTable, setTrainTable] = useState('');
  const [valCatalog, setValCatalog] = useState('');
  const [valSchema, setValSchema] = useState('');
  const [valTable, setValTable] = useState('');

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<FormErrors>({});

  // Calculate total weightage
  const totalWeightage = scoringFunctions.reduce((sum, sf) => sum + sf.weightage, 0);

  const addConfigParam = () => {
    const key = `param_${Object.keys(optimizerConfig).length + 1}`;
    setOptimizerConfig({ ...optimizerConfig, [key]: '' });
  };

  const updateConfigParam = (oldKey: string, newKey: string, value: string) => {
    const newConfig = { ...optimizerConfig };
    delete newConfig[oldKey];
    newConfig[newKey] = value;
    setOptimizerConfig(newConfig);
  };

  const removeConfigParam = (key: string) => {
    const newConfig = { ...optimizerConfig };
    delete newConfig[key];
    setOptimizerConfig(newConfig);
  };

  const addScoringFunction = () => {
    const newSF: ScoringFunction = {
      id: Date.now().toString(),
      type: 'Correctness',
      name: '',
      weightage: 0
    };
    setScoringFunctions([...scoringFunctions, newSF]);
  };

  const updateScoringFunction = (id: string, updates: Partial<ScoringFunction>) => {
    setScoringFunctions(scoringFunctions.map(sf =>
      sf.id === id ? { ...sf, ...updates } : sf
    ));
  };

  const removeScoringFunction = (id: string) => {
    setScoringFunctions(scoringFunctions.filter(sf => sf.id !== id));
  };

  const handleOptimizerChange = (newOptimizer: OptimizerType) => {
    setOptimizerName(newOptimizer);
    // Reset config to defaults for the selected optimizer
    setOptimizerConfig(DEFAULT_OPTIMIZER_CONFIGS[newOptimizer]);
  };

  const handleSubmit = async () => {
    if (!workflowId) {
      setErrors({ general: 'Please save your workflow before optimizing.' });
      return;
    }

    if (!workflowIR) {
      setErrors({ general: 'Workflow data is not available.' });
      return;
    }

    if (isOptimizationActive) {
      setErrors({ general: 'An optimization is already running for this workflow. Please wait for it to complete.' });
      return;
    }

    // Clear previous errors
    setErrors({});

    // Validate weightage totals 100
    if (totalWeightage !== 100) {
      setErrors({ weightage: `Total weightage must equal 100 (current: ${totalWeightage})` });
      return;
    }

    setIsSubmitting(true);

    try {
      const payload = {
        workflow_id: workflowId,
        workflow_ir: workflowIR,
        optimizer_name: optimizerName,
        optimizer_config: optimizerConfig,
        scoring_functions: scoringFunctions.map(sf => ({
          type: sf.type,
          name: sf.name,
          guideline: sf.type === 'Guidelines' ? sf.guideline : undefined,
          weightage: sf.weightage
        })),
        training_data: {
          catalog: trainCatalog,
          schema: trainSchema,
          table: trainTable
        },
        validation_data: {
          catalog: valCatalog,
          schema: valSchema,
          table: valTable
        }
      };

      const response = await fetch('/api/v1/workflows/optimize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      const result = await response.json();

      if (response.ok) {
        // Success - notify parent and close modal
        if (onOptimizationStart && result.optimization_id) {
          onOptimizationStart(result.optimization_id);
        }
        onClose();
      } else {
        // Handle validation errors from backend
        // The backend returns either:
        // 1. { detail: string } for simple errors
        // 2. { detail: { detail: string, field_errors: {...} } } for validation errors
        if (result.detail && typeof result.detail === 'object') {
          // Nested detail object with field errors
          const errorDetail = result.detail.detail || 'Validation failed';
          const fieldErrors = result.detail.field_errors || {};
          setErrors({ general: errorDetail, ...fieldErrors });
        } else if (result.field_errors) {
          // Direct field errors
          setErrors(result.field_errors);
        } else {
          // Simple error message
          setErrors({ general: result.detail || 'Optimization failed' });
        }
      }
    } catch (error) {
      setErrors({ general: 'Network error. Please try again.' });
      console.error('Optimization error:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-200 bg-gradient-to-r from-slate-50 to-white">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-brand-100 rounded-lg">
              <Zap size={20} className="text-brand-600" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-slate-900">Optimize Workflow</h3>
              <p className="text-sm text-slate-500">Configure optimization parameters</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
            disabled={isSubmitting}
          >
            <X size={20} className="text-slate-500" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6">
          {errors.general && (
            <div className="mb-4 p-3 bg-coral-50 border border-coral-200 rounded-lg text-coral-800 text-sm">
              {errors.general}
            </div>
          )}

          <div className="space-y-6">
            {/* Optimizer Selection */}
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Optimizer Type <span className="text-brand-500">*</span>
              </label>
              <select
                value={optimizerName}
                onChange={(e) => handleOptimizerChange(e.target.value as OptimizerType)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500 bg-white"
                disabled={isSubmitting}
              >
                {OptimizerTypes.map(type => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
              {errors.optimizer_name && (
                <p className="mt-1 text-sm text-coral-600">{errors.optimizer_name}</p>
              )}
            </div>

            {/* Optimizer Config */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-semibold text-slate-700">
                  Optimizer Configuration
                </label>
                <button
                  onClick={addConfigParam}
                  className="text-sm text-brand-600 hover:text-brand-700 font-medium flex items-center space-x-1"
                  disabled={isSubmitting}
                >
                  <Plus size={14} />
                  <span>Add Parameter</span>
                </button>
              </div>
              <div className="space-y-2 bg-slate-50 rounded-lg p-3">
                {Object.entries(optimizerConfig).length === 0 ? (
                  <p className="text-sm text-slate-500 text-center py-2">No parameters added</p>
                ) : (
                  Object.entries(optimizerConfig).map(([key, value]) => (
                    <div key={key} className="flex items-center space-x-2">
                      <input
                        type="text"
                        value={key}
                        onChange={(e) => updateConfigParam(key, e.target.value, value)}
                        placeholder="Parameter name"
                        className="flex-1 px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500 bg-white text-sm"
                        disabled={isSubmitting}
                      />
                      <input
                        type="text"
                        value={value}
                        onChange={(e) => updateConfigParam(key, key, e.target.value)}
                        placeholder="Value"
                        className="flex-1 px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500 bg-white text-sm"
                        disabled={isSubmitting}
                      />
                      <button
                        onClick={() => removeConfigParam(key)}
                        className="p-2 text-coral-600 hover:bg-coral-50 rounded-lg transition-colors"
                        disabled={isSubmitting}
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  ))
                )}
              </div>
              {errors.optimizer_config && (
                <p className="mt-1 text-sm text-coral-600">{errors.optimizer_config}</p>
              )}
            </div>

            {/* Scoring Functions */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-semibold text-slate-700">
                  Scoring Functions <span className="text-brand-500">*</span>
                </label>
                <div className="flex items-center space-x-4">
                  <span className={`text-sm font-medium ${totalWeightage === 100 ? 'text-emerald-600' : 'text-amber-600'}`}>
                    Total: {totalWeightage}%
                  </span>
                  <button
                    onClick={addScoringFunction}
                    className="text-sm text-brand-600 hover:text-brand-700 font-medium flex items-center space-x-1"
                    disabled={isSubmitting}
                  >
                    <Plus size={14} />
                    <span>Add Function</span>
                  </button>
                </div>
              </div>
              <div className="space-y-3 bg-slate-50 rounded-lg p-3">
                {scoringFunctions.map((sf) => (
                  <div key={sf.id} className="bg-white rounded-lg p-3 border border-slate-200">
                    <div className="grid grid-cols-3 gap-3 mb-2">
                      <div>
                        <label className="block text-xs font-medium text-slate-600 mb-1">Type</label>
                        <select
                          value={sf.type}
                          onChange={(e) => updateScoringFunction(sf.id, { type: e.target.value as 'Correctness' | 'Guidelines' })}
                          className="w-full px-2 py-1.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500 text-sm bg-white"
                          disabled={isSubmitting}
                        >
                          <option value="Correctness">Correctness</option>
                          <option value="Guidelines">Guidelines</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-slate-600 mb-1">Name</label>
                        <input
                          type="text"
                          value={sf.name}
                          onChange={(e) => updateScoringFunction(sf.id, { name: e.target.value })}
                          placeholder="Function name"
                          className="w-full px-2 py-1.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500 text-sm"
                          disabled={isSubmitting}
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-slate-600 mb-1">Weightage (%)</label>
                        <div className="flex items-center space-x-2">
                          <input
                            type="number"
                            value={sf.weightage}
                            onChange={(e) => updateScoringFunction(sf.id, { weightage: parseInt(e.target.value) || 0 })}
                            min="0"
                            max="100"
                            className="flex-1 px-2 py-1.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500 text-sm"
                            disabled={isSubmitting}
                          />
                          <button
                            onClick={() => removeScoringFunction(sf.id)}
                            className="p-1.5 text-coral-600 hover:bg-coral-50 rounded-lg transition-colors"
                            disabled={isSubmitting}
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>
                    </div>
                    {sf.type === 'Guidelines' && (
                      <div>
                        <label className="block text-xs font-medium text-slate-600 mb-1">Guideline</label>
                        <textarea
                          value={sf.guideline || ''}
                          onChange={(e) => updateScoringFunction(sf.id, { guideline: e.target.value })}
                          placeholder="Enter guideline in plain text..."
                          className="w-full px-2 py-1.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500 text-sm resize-none"
                          rows={2}
                          disabled={isSubmitting}
                        />
                      </div>
                    )}
                  </div>
                ))}
              </div>
              {errors.weightage && (
                <p className="mt-1 text-sm text-coral-600">{errors.weightage}</p>
              )}
              {errors.scoring_functions && (
                <p className="mt-1 text-sm text-coral-600">{errors.scoring_functions}</p>
              )}
            </div>

            {/* Training Dataset */}
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Training Dataset <span className="text-brand-500">*</span>
              </label>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Catalog</label>
                  <input
                    type="text"
                    value={trainCatalog}
                    onChange={(e) => setTrainCatalog(e.target.value)}
                    placeholder="main"
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500 text-sm"
                    disabled={isSubmitting}
                  />
                  {errors.train_catalog && (
                    <p className="mt-1 text-xs text-coral-600">{errors.train_catalog}</p>
                  )}
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Schema</label>
                  <input
                    type="text"
                    value={trainSchema}
                    onChange={(e) => setTrainSchema(e.target.value)}
                    placeholder="default"
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500 text-sm"
                    disabled={isSubmitting}
                  />
                  {errors.train_schema && (
                    <p className="mt-1 text-xs text-coral-600">{errors.train_schema}</p>
                  )}
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Table</label>
                  <input
                    type="text"
                    value={trainTable}
                    onChange={(e) => setTrainTable(e.target.value)}
                    placeholder="trainset"
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500 text-sm"
                    disabled={isSubmitting}
                  />
                  {errors.train_table && (
                    <p className="mt-1 text-xs text-coral-600">{errors.train_table}</p>
                  )}
                </div>
              </div>
            </div>

            {/* Validation Dataset */}
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Validation Dataset <span className="text-brand-500">*</span>
              </label>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Catalog</label>
                  <input
                    type="text"
                    value={valCatalog}
                    onChange={(e) => setValCatalog(e.target.value)}
                    placeholder="main"
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500 text-sm"
                    disabled={isSubmitting}
                  />
                  {errors.val_catalog && (
                    <p className="mt-1 text-xs text-coral-600">{errors.val_catalog}</p>
                  )}
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Schema</label>
                  <input
                    type="text"
                    value={valSchema}
                    onChange={(e) => setValSchema(e.target.value)}
                    placeholder="default"
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500 text-sm"
                    disabled={isSubmitting}
                  />
                  {errors.val_schema && (
                    <p className="mt-1 text-xs text-coral-600">{errors.val_schema}</p>
                  )}
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Table</label>
                  <input
                    type="text"
                    value={valTable}
                    onChange={(e) => setValTable(e.target.value)}
                    placeholder="valset"
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500 text-sm"
                    disabled={isSubmitting}
                  />
                  {errors.val_table && (
                    <p className="mt-1 text-xs text-coral-600">{errors.val_table}</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end space-x-3 p-5 border-t border-slate-200 bg-slate-50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors font-medium"
            disabled={isSubmitting}
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={isSubmitting || totalWeightage !== 100}
            className="px-5 py-2 bg-brand-500 text-white rounded-lg hover:bg-brand-600 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors font-medium flex items-center space-x-2"
          >
            {isSubmitting ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                <span>Submitting...</span>
              </>
            ) : (
              <>
                <Zap size={16} />
                <span>Start Optimization</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default OptimizeModal;
