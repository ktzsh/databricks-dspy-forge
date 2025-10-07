import React from 'react';
import { Plus, X } from 'lucide-react';
import { StructuredCondition, ComparisonOperator, LogicalOperator, SignatureField } from '../types/workflow';

interface ConditionBuilderProps {
  conditions: StructuredCondition[];
  onChange: (conditions: StructuredCondition[]) => void;
  availableFields: SignatureField[];
}

const comparisonOperators: { value: ComparisonOperator; label: string }[] = [
  { value: '==', label: 'equals (==)' },
  { value: '!=', label: 'not equals (!=)' },
  { value: '>', label: 'greater than (>)' },
  { value: '<', label: 'less than (<)' },
  { value: '>=', label: 'greater or equal (>=)' },
  { value: '<=', label: 'less or equal (<=)' },
  { value: 'contains', label: 'contains' },
  { value: 'not_contains', label: 'not contains' },
  { value: 'in', label: 'in list' },
  { value: 'not_in', label: 'not in list' },
  { value: 'startswith', label: 'starts with' },
  { value: 'endswith', label: 'ends with' },
  { value: 'is_empty', label: 'is empty' },
  { value: 'is_not_empty', label: 'is not empty' },
];

const logicalOperators: { value: LogicalOperator; label: string }[] = [
  { value: 'AND', label: 'AND' },
  { value: 'OR', label: 'OR' },
];

const ConditionBuilder: React.FC<ConditionBuilderProps> = ({
  conditions,
  onChange,
  availableFields,
}) => {
  const addCondition = () => {
    const newCondition: StructuredCondition = {
      field: availableFields[0]?.name || '',
      operator: '==',
      value: '',
      logicalOp: conditions.length > 0 ? 'AND' : undefined,
    };
    onChange([...conditions, newCondition]);
  };

  const removeCondition = (index: number) => {
    onChange(conditions.filter((_, i) => i !== index));
  };

  const updateCondition = (index: number, updates: Partial<StructuredCondition>) => {
    onChange(
      conditions.map((cond, i) => (i === index ? { ...cond, ...updates } : cond))
    );
  };

  const needsValue = (operator: ComparisonOperator) => {
    return !['is_empty', 'is_not_empty'].includes(operator);
  };

  const getFieldType = (fieldName: string): string => {
    const field = availableFields.find((f) => f.name === fieldName);
    return field?.type || 'str';
  };

  const renderValueInput = (condition: StructuredCondition, index: number) => {
    if (!needsValue(condition.operator)) {
      return null;
    }

    const fieldType = getFieldType(condition.field);
    const isNumeric = ['int', 'float'].includes(fieldType);
    const isList = condition.operator === 'in' || condition.operator === 'not_in';

    return (
      <input
        type={isNumeric && !isList ? 'number' : 'text'}
        value={condition.value?.toString() || ''}
        onChange={(e) => {
          let value: any = e.target.value;
          if (isList) {
            // Parse comma-separated values for list operators
            value = value.split(',').map((v: string) => v.trim()).filter((v: string) => v);
          } else if (isNumeric) {
            value = fieldType === 'int' ? parseInt(value) || 0 : parseFloat(value) || 0;
          }
          updateCondition(index, { value });
        }}
        placeholder={isList ? 'value1, value2, ...' : 'value'}
        className="flex-1 px-2 py-1 border border-gray-300 rounded text-sm"
      />
    );
  };

  const generatePreview = () => {
    if (conditions.length === 0) return 'No conditions';

    return conditions
      .map((cond, idx) => {
        const prefix = idx > 0 ? ` ${conditions[idx - 1].logicalOp} ` : '';
        const valueStr = needsValue(cond.operator)
          ? ` ${JSON.stringify(cond.value)}`
          : '';
        return `${prefix}${cond.field} ${cond.operator}${valueStr}`;
      })
      .join('');
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium">Conditions</label>
        <button
          onClick={addCondition}
          disabled={availableFields.length === 0}
          className="flex items-center space-x-1 px-2 py-1 bg-purple-500 text-white rounded text-xs hover:bg-purple-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
        >
          <Plus size={12} />
          <span>Add</span>
        </button>
      </div>

      {availableFields.length === 0 ? (
        <div className="text-sm text-gray-500 p-2 border border-gray-200 rounded">
          Connect to a SignatureField node to see available fields
        </div>
      ) : (
        <>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {conditions.map((condition, index) => (
              <div key={index} className="border border-gray-200 rounded p-2 space-y-2">
                {/* Logical operator for chaining (shown for all except first) */}
                {index > 0 && (
                  <div className="flex items-center space-x-2">
                    <span className="text-xs text-gray-600">Combine with previous using:</span>
                    <select
                      value={conditions[index - 1].logicalOp || 'AND'}
                      onChange={(e) =>
                        updateCondition(index - 1, { logicalOp: e.target.value as LogicalOperator })
                      }
                      className="px-2 py-1 border border-purple-300 bg-purple-50 rounded text-xs font-semibold"
                    >
                      {logicalOperators.map((op) => (
                        <option key={op.value} value={op.value}>
                          {op.label}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                {/* Main condition row */}
                <div className="flex items-center space-x-2">
                  {/* Field selector */}
                  <select
                    value={condition.field}
                    onChange={(e) => updateCondition(index, { field: e.target.value })}
                    className="flex-1 px-2 py-1 border border-gray-300 rounded text-sm"
                  >
                    {availableFields.map((field) => (
                      <option key={field.name} value={field.name}>
                        {field.name} ({field.type})
                      </option>
                    ))}
                  </select>

                  {/* Operator selector */}
                  <select
                    value={condition.operator}
                    onChange={(e) =>
                      updateCondition(index, { operator: e.target.value as ComparisonOperator })
                    }
                    className="flex-1 px-2 py-1 border border-gray-300 rounded text-sm"
                  >
                    {comparisonOperators.map((op) => (
                      <option key={op.value} value={op.value}>
                        {op.label}
                      </option>
                    ))}
                  </select>

                  {/* Value input (if needed) */}
                  {renderValueInput(condition, index)}

                  {/* Remove button */}
                  <button
                    onClick={() => removeCondition(index)}
                    className="p-1 text-red-500 hover:bg-red-50 rounded"
                    title="Remove condition"
                  >
                    <X size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Preview */}
          {conditions.length > 0 && (
            <div className="mt-2">
              <div className="text-xs font-medium text-gray-600 mb-1">Preview:</div>
              <div className="p-2 bg-purple-50 border border-purple-200 rounded text-xs font-mono">
                {generatePreview()}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default ConditionBuilder;
