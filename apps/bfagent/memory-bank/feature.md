# BookFactory Features

## 📋 Core Features

**Project**: BookFactory AI Book Development
**Status**: 🏗️ Phase 1 Implementation
**Framework**: AutoGen + L2MAC + CrewAI
**Last Updated**: Jan 27, 2025

## 🎯 Primary Features

### 1. Multi-Agent Book Writing
- **Researcher Agent**: Automated research and fact-checking
- **Outliner Agent**: Book structure and chapter planning
- **L2MAC Writer**: Unlimited length content generation
- **Editor Agent**: Professional editing and refinement

### 2. Memory Bank Integration
- Persistent project storage across sessions
- Context sharing between agents
- Cross-session continuity
- Windsurf optimization

### 3. Web Interface
- Streamlit-based dashboard
- Real-time agent monitoring
- Project management
- Memory bank viewer

### Success Metrics
- Generate 10,000+ word chapters without context limits
- Maintain consistency across multi-chapter books
- <30 seconds agent response time
- 95% content quality score

## 📐 Technical Design

### Architecture Overview
```
WorkflowBuilder/
├── Canvas/              # Main drawing area
│   ├── Grid            # Background grid system
│   ├── ViewControls    # Zoom, pan, fit
│   └── SelectionBox    # Multi-select functionality
├── NodePalette/        # Draggable nodes
│   ├── TriggerNodes
│   ├── ActionNodes
│   └── ControlNodes
├── NodeEditor/         # Node configuration
│   ├── ConfigPanel
│   ├── ValidationUI
│   └── TestRunner
└── Toolbar/           # Actions and tools
    ├── SaveControls
    ├── VersionHistory
    └── ShareOptions
```

### State Management
```typescript
interface WorkflowBuilderState {
  // Canvas State
  canvas: {
    zoom: number;
    position: { x: number; y: number };
    gridSize: number;
    snapToGrid: boolean;
  };

  // Workflow State
  workflow: {
    id: string;
    name: string;
    nodes: Map<string, Node>;
    connections: Connection[];
    metadata: WorkflowMetadata;
  };

  // UI State
  ui: {
    selectedNodes: Set<string>;
    selectedConnection: string | null;
    isDragging: boolean;
    isConnecting: boolean;
    activePanel: 'palette' | 'editor' | null;
  };

  // Validation State
  validation: {
    errors: ValidationError[];
    warnings: ValidationWarning[];
    isValid: boolean;
  };
}
```

### Component Hierarchy
```typescript
<WorkflowBuilder>
  <DndProvider backend={HTML5Backend}>
    <div className="workflow-builder">
      <Toolbar />
      <div className="builder-body">
        <NodePalette />
        <Canvas>
          <Grid />
          <Connections />
          <Nodes />
          <SelectionBox />
        </Canvas>
        <NodeEditor />
      </div>
    </div>
  </DndProvider>
</WorkflowBuilder>
```

## 🛠️ Implementation Details

### Node System
```typescript
// Base node structure
interface WorkflowNode {
  id: string;
  type: 'trigger' | 'action' | 'control';
  position: { x: number; y: number };
  config: Record<string, any>;
  inputs: PortDefinition[];
  outputs: PortDefinition[];
  metadata: {
    label: string;
    description: string;
    icon: string;
    color: string;
  };
}

// Node implementation example
export const EmailTriggerNode: NodeDefinition = {
  type: 'trigger',
  category: 'communication',
  metadata: {
    label: 'Email Trigger',
    description: 'Triggers workflow when email received',
    icon: 'mail',
    color: '#3B82F6'
  },
  config: {
    schema: z.object({
      from: z.string().email().optional(),
      subject: z.string().optional(),
      contains: z.string().optional()
    })
  },
  outputs: [{
    id: 'email',
    type: 'email',
    label: 'Email Data'
  }]
};
```

### Drag and Drop Implementation
```typescript
// Draggable node from palette
const DraggableNode: React.FC<NodeProps> = ({ node }) => {
  const [{ isDragging }, drag] = useDrag({
    type: 'node',
    item: { type: node.type, nodeType: node.nodeType },
    collect: (monitor) => ({
      isDragging: monitor.isDragging()
    })
  });

  return (
    <div ref={drag} className={cn('node-item', { dragging: isDragging })}>
      <Icon name={node.icon} />
      <span>{node.label}</span>
    </div>
  );
};

// Droppable canvas
const Canvas: React.FC = ({ children }) => {
  const [{ isOver }, drop] = useDrop({
    accept: 'node',
    drop: (item, monitor) => {
      const position = monitor.getClientOffset();
      handleNodeDrop(item, position);
    },
    collect: (monitor) => ({
      isOver: monitor.isOver()
    })
  });

  return (
    <div ref={drop} className={cn('canvas', { 'drop-active': isOver })}>
      {children}
    </div>
  );
};
```

### Connection System
```typescript
// Connection validation
export function validateConnection(
  source: PortDefinition,
  target: PortDefinition
): ValidationResult {
  // Type compatibility check
  if (!isCompatibleType(source.type, target.type)) {
    return {
      valid: false,
      error: `Cannot connect ${source.type} to ${target.type}`
    };
  }

  // Prevent cycles
  if (wouldCreateCycle(source.nodeId, target.nodeId)) {
    return {
      valid: false,
      error: 'Connection would create a cycle'
    };
  }

  return { valid: true };
}

// Connection rendering
const Connection: React.FC<ConnectionProps> = ({ connection }) => {
  const path = calculateBezierPath(
    connection.source,
    connection.target
  );

  return (
    <g className="connection">
      <path
        d={path}
        className="connection-line"
        onClick={() => handleConnectionClick(connection.id)}
      />
      <circle
        cx={connection.midpoint.x}
        cy={connection.midpoint.y}
        r={4}
        className="connection-handle"
      />
    </g>
  );
};
```

## 🎨 UI/UX Specifications

### Visual Design
- **Grid**: 20px squares, #E5E7EB color, 0.5 opacity
- **Nodes**: Rounded corners (8px), drop shadow, hover effects
- **Connections**: Bezier curves, 2px stroke, animated on hover
- **Selection**: Blue outline (#3B82F6), 2px dashed

### Interactions
1. **Drag Node**: Shows ghost image, snap to grid
2. **Connect Nodes**: Drag from output to input port
3. **Pan Canvas**: Hold space + drag or middle mouse
4. **Zoom**: Ctrl+Scroll or zoom controls
5. **Multi-select**: Shift+Click or drag selection box

### Keyboard Shortcuts
- `Delete`: Remove selected nodes/connections
- `Ctrl+C/V`: Copy/paste nodes
- `Ctrl+Z/Y`: Undo/redo
- `Ctrl+S`: Save workflow
- `Space`: Pan mode
- `F`: Fit to screen

## 🧪 Testing Strategy

### Unit Tests
```typescript
describe('WorkflowBuilder', () => {
  describe('Node Operations', () => {
    it('should add node on drop', async () => {
      const { getByTestId } = render(<WorkflowBuilder />);

      const nodeItem = getByTestId('node-email-trigger');
      const canvas = getByTestId('canvas');

      fireEvent.dragStart(nodeItem);
      fireEvent.drop(canvas, {
        clientX: 100,
        clientY: 100
      });

      expect(getByTestId('node-1')).toBeInTheDocument();
    });
  });

  describe('Connection Validation', () => {
    it('should prevent invalid connections', () => {
      const result = validateConnection(
        { type: 'string', nodeId: 'node-1' },
        { type: 'number', nodeId: 'node-2' }
      );

      expect(result.valid).toBe(false);
    });
  });
});
```

### E2E Tests
```typescript
test('complete workflow creation flow', async ({ page }) => {
  await page.goto('/workflows/new');

  // Drag email trigger
  await page.dragAndDrop(
    '[data-testid="node-email-trigger"]',
    '[data-testid="canvas"]'
  );

  // Configure node
  await page.click('[data-testid="node-1"]');
  await page.fill('[name="from"]', 'customer@example.com');

  // Add action node
  await page.dragAndDrop(
    '[data-testid="node-send-slack"]',
    '[data-testid="canvas"]'
  );

  // Connect nodes
  await page.dragAndDrop(
    '[data-testid="node-1-output"]',
    '[data-testid="node-2-input"]'
  );

  // Save workflow
  await page.click('[data-testid="save-workflow"]');
  await expect(page.locator('.toast-success')).toBeVisible();
});
```

## 🐛 Known Issues

1. **Performance degradation with 100+ nodes**
   - Status: Investigating
   - Workaround: Implement viewport culling

2. **Connection paths overlap with nodes**
   - Status: In progress
   - Solution: Implement path routing algorithm

3. **Undo/redo memory leak**
   - Status: Fixed in dev
   - Fix: Limit history to 50 actions

## 🚀 Rollout Plan

### Phase 1: Alpha (Current)
- Internal team testing
- Basic node types only
- Limited to 50 nodes

### Phase 2: Beta (Feb 1)
- 50 selected users
- All node types available
- Performance improvements

### Phase 3: GA (Feb 15)
- All users
- Template library
- Advanced features

## 📊 Performance Targets

- Initial render: <500ms
- Node drag: 60fps
- Connection validation: <50ms
- Save operation: <1s
- Max nodes: 200
- Max connections: 500

## 🔗 Related Documents

- [Node Type Catalog](./node-types.md)
- [Workflow Engine Spec](./workflow-engine.md)
- [API Integration Guide](@api-contracts.md)
- [UI Component Library](./ui-components.md)

## 💡 Future Enhancements

1. **Subworkflows**: Nest workflows within workflows
2. **Debugging Mode**: Step through execution
3. **Version Control**: Git-like branching
4. **Collaboration**: Real-time multi-user editing
5. **AI Assistant**: Natural language to workflow
6. **Mobile Editor**: Touch-optimized interface

---

*Feature documentation maintained by Development Team*
*Last reviewed: Jan 25, 2024*
