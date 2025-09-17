import { NodeTypes } from 'reactflow';
import SignatureFieldNode from './SignatureFieldNode';
import ModuleNode from './ModuleNode';
import LogicNode from './LogicNode';

export const nodeTypes: NodeTypes = {
  signature_field: SignatureFieldNode,
  module: ModuleNode,
  logic: LogicNode,
};

export { SignatureFieldNode, ModuleNode, LogicNode };