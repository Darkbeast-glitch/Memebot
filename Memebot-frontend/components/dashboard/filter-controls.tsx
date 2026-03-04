'use client'

import { Slider } from '@/components/ui/slider'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Card } from '@/components/ui/card'

interface FilterControlsProps {
  minScore: number
  onMinScoreChange: (value: number) => void
  minLiquidity: number
  onMinLiquidityChange: (value: number) => void
  behaviourPassedOnly: boolean
  onBehaviourPassedOnlyChange: (value: boolean) => void
}

export default function FilterControls({
  minScore,
  onMinScoreChange,
  minLiquidity,
  onMinLiquidityChange,
  behaviourPassedOnly,
  onBehaviourPassedOnlyChange,
}: FilterControlsProps) {
  return (
    <Card className="mb-6 bg-card p-6">
      <h2 className="mb-6 text-lg font-semibold text-foreground">
        Filter Controls
      </h2>

      <div className="space-y-6">
        {/* Minimum Score Slider */}
        <div>
          <div className="mb-3 flex items-center justify-between">
            <Label htmlFor="min-score" className="text-sm font-medium text-foreground">
              Minimum Score
            </Label>
            <span className="inline-flex items-center rounded bg-secondary px-2.5 py-0.5 text-sm font-semibold text-secondary-foreground">
              {minScore}
            </span>
          </div>
          <Slider
            id="min-score"
            min={0}
            max={15}
            step={1}
            value={[minScore]}
            onValueChange={(value) => onMinScoreChange(value[0])}
            className="w-full"
          />
          <p className="mt-1 text-xs text-muted-foreground">
            Range: 0 - 15
          </p>
        </div>

        {/* Minimum Liquidity Input */}
        <div>
          <Label htmlFor="min-liquidity" className="mb-2 block text-sm font-medium text-foreground">
            Minimum Liquidity (USD)
          </Label>
          <Input
            id="min-liquidity"
            type="number"
            value={minLiquidity}
            onChange={(e) => onMinLiquidityChange(Number(e.target.value))}
            className="w-full bg-input text-foreground"
            step="50000"
          />
          <p className="mt-1 text-xs text-muted-foreground">
            ${minLiquidity.toLocaleString()}
          </p>
        </div>

        {/* Behaviour Passed Only Toggle */}
        <div className="flex items-center justify-between rounded-lg bg-secondary/20 p-3">
          <Label htmlFor="behaviour-passed" className="text-sm font-medium text-foreground cursor-pointer">
            Show Only Behaviour Passed
          </Label>
          <Switch
            id="behaviour-passed"
            checked={behaviourPassedOnly}
            onCheckedChange={onBehaviourPassedOnlyChange}
          />
        </div>
      </div>
    </Card>
  )
}
