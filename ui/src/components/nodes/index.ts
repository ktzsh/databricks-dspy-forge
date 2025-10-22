import { NodeTypes } from 'reactflow';
import SignatureFieldNode from './SignatureFieldNode';
import ModuleNode from './ModuleNode';
import LogicNode from './LogicNode';
import RetrieverNode from './RetrieverNode';
import ToolNode from './ToolNode';

export const nodeTypes: NodeTypes = {
  signature_field: SignatureFieldNode,
  module: ModuleNode,
  logic: LogicNode,
  retriever: RetrieverNode,
  tool: ToolNode,
};

export { SignatureFieldNode, ModuleNode, LogicNode, RetrieverNode, ToolNode };