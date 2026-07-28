# CTV ONE Accessibility Standard

Sprint: 2.0.1 UX Foundation and Information Architecture  
Scope: Accessibility requirements for the portal and Super Admin IAM.

## Target

CTV ONE should meet WCAG 2.2 AA for all core portal and Super Admin IAM workflows.

## Keyboard

Requirements:

- Every interactive element is reachable by keyboard.
- Focus order follows visual order.
- Focus state is clearly visible against dark backgrounds.
- Modals trap focus and return focus to the invoking control.
- Escape closes dismissible overlays.
- Tables support row focus and row action access.
- Wizards support keyboard navigation without losing form state.

## Screen Readers

Requirements:

- Page has one `h1`.
- Sections use semantic headings.
- Icon-only buttons have accessible names.
- Status badges include text, not color-only meaning.
- Form inputs have labels and error descriptions.
- Permission Matrix cells expose row name, column name, and state.
- Toasts and async save states use appropriate live regions.

## Color And Contrast

Minimums:

- Body text: 4.5:1 contrast ratio.
- Large text: 3:1 contrast ratio.
- Non-text controls and focus rings: 3:1 contrast ratio.
- Error and success states include icon or text in addition to color.

Dark UI requirements:

- Muted text cannot be used for required values.
- Orange accent cannot be the only indicator of active state.
- Disabled controls need opacity plus explanation on hover or inline helper.

## Forms

Form rules:

- Required fields are indicated in text.
- Errors appear next to the relevant field.
- Error summaries appear at the top of multi-step forms.
- Validation does not depend on color alone.
- Inputs should not clear on failed submit.
- Numeric quota fields accept keyboard entry as well as stepper controls.

## Tables

Table rules:

- Column headers are programmatically associated with cells.
- Sort state is announced.
- Row action menus are keyboard accessible.
- Bulk selection communicates selected count.
- Empty and filtered-empty states are distinct.
- Horizontal scroll areas have visible affordance and keyboard access.

## Motion

Motion rules:

- Respect reduced-motion preferences.
- Avoid flashing or pulsing status indicators.
- Use subtle transitions for navigation and drawer open states only.
- Loading states should not create focus loss.

## Confirmation And Risk

High-risk admin actions must provide:

- Clear action title.
- Target name.
- Consequence summary.
- Required reason when configured.
- Keyboard-accessible cancel and confirm buttons.
- Focus starts on the safest action.

## Plain Language

Accessibility includes comprehension.

Use:

- "Suspend access" instead of "Deactivate actor".
- "Grant knowledge access" instead of "Hydrate corpus scope".
- "Quota resets monthly" instead of "Periodic allowance recurs".
- "This role affects 18 users" instead of "Role has 18 bindings".

## Accessibility Review Checklist

Before implementation acceptance:

- Keyboard-only user can create a user.
- Keyboard-only user can edit role permissions.
- Screen reader can understand Permission Matrix cells.
- User can identify errors without color.
- User can complete the Create User Wizard at 390 px width.
- Modal confirmations restore focus.
- Audit Activity can be filtered and opened without pointer input.
- Professional AI Identity status is announced as text.

