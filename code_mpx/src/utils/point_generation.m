% 生成等边三角形并绘制圆覆盖坐标系
clear; clc; close all;

% 设置参数
x_range = [0, 10];
y_range = [0, 10];
radius = 1.5;
center_distance = 3; % 顶点到中心的距离

% 以(5,5)为中心生成等边三角形
center_x = 5.5;
center_y = 5.5;

% 生成随机旋转角度（0-360度）
%random_angle = rand() * 360;
random_angle = 15;
fprintf('随机旋转角度: %.2f°\n', random_angle);

% 将角度转换为弧度
angle_rad = deg2rad(random_angle);

% 计算等边三角形的顶点坐标（未旋转时）
% 三个顶点在圆周上均匀分布，初始位置：一个点在上方
theta1 = -pi/2;  % 上方
theta2 = -pi/2 + 2*pi/3;  % 左下方
theta3 = -pi/2 + 4*pi/3;  % 右下方

% 应用随机旋转
theta1_rotated = theta1 + angle_rad;
theta2_rotated = theta2 + angle_rad;
theta3_rotated = theta3 + angle_rad;

% 计算旋转后的顶点坐标
x1 = center_x + center_distance * cos(theta1_rotated);
y1 = center_y + center_distance * sin(theta1_rotated);

x2 = center_x + center_distance * cos(theta2_rotated);
y2 = center_y + center_distance * sin(theta2_rotated);

x3 = center_x + center_distance * cos(theta3_rotated);
y3 = center_y + center_distance * sin(theta3_rotated);

% 存储点坐标
points = [x1, y1; x2, y2; x3, y3];

% 为每个圆生成随机直径
diameter_endpoints = cell(3, 1); % 存储每个圆的直径端点
diameter_angles = [rand() * 180 0 0];   % 存储每个圆的直径角度

for i = 1:3
    % 生成随机直径角度（0-180度）
    if i==1
        diameter_angle = diameter_angles(1);
    else
        diameter_angle = diameter_angles(1) + (i-1)*120;
        diameter_angles(i) = diameter_angle;
    end
    
    % 计算直径的两个端点
    angle_rad_diam = deg2rad(diameter_angle);
    dx = radius * cos(angle_rad_diam);
    dy = radius * sin(angle_rad_diam);
    
    % 端点1
    end1_x = points(i,1) + dx;
    end1_y = points(i,2) + dy;
    
    % 端点2
    end2_x = points(i,1) - dx;
    end2_y = points(i,2) - dy;
    
    diameter_endpoints{i} = [end1_x, end1_y; end2_x, end2_y];
end

% 绘制图形
figure('Position', [100, 100, 800, 800]);
hold on;
grid on;
axis equal;

% 绘制坐标系范围
rectangle('Position', [x_range(1), y_range(1), diff(x_range), diff(y_range)], ...
          'EdgeColor', 'k', 'LineWidth', 2, 'LineStyle', '--');

% 绘制中心点
plot(center_x, center_y, 'ko', 'MarkerSize', 8, 'MarkerFaceColor', 'k');
text(center_x, center_y+0.3, '中心(5,5)', 'FontSize', 12, 'HorizontalAlignment', 'center');

% 绘制等边三角形
plot([x1, x2, x3, x1], [y1, y2, y3, y1], 'b-', 'LineWidth', 2);

% 绘制三个圆
theta = 0:0.01:2*pi;
colors = ['r', 'g', 'b']; % 不同颜色区分三个圆

for i = 1:3
    x_circle = points(i,1) + radius * cos(theta);
    y_circle = points(i,2) + radius * sin(theta);
    plot(x_circle, y_circle, 'r-', 'LineWidth', 1.5);
    
    % 填充圆区域（半透明）
    fill(x_circle, y_circle, 'r', 'FaceAlpha', 0.2, 'EdgeColor', 'r');

    % 绘制直径
    endpoints = diameter_endpoints{i};
    plot([endpoints(1,1), endpoints(2,1)], [endpoints(1,2), endpoints(2,2)], ...
         [colors(i) '-'], 'LineWidth', 3);
    
    % 标记直径端点
    scatter(endpoints(:,1), endpoints(:,2), 120, colors(i), 'filled', 's'); % 方形标记
    
    % 标注端点坐标
    text(endpoints(1,1), endpoints(1,2)+0.25, ...
         sprintf('(%.2f,%.2f)', endpoints(1,1), endpoints(1,2)), ...
         'FontSize', 10, 'Color', colors(i), 'HorizontalAlignment', 'center', ...
         'BackgroundColor', 'white', 'EdgeColor', colors(i));
    text(endpoints(2,1), endpoints(2,2)-0.25, ...
         sprintf('(%.2f,%.2f)', endpoints(2,1), endpoints(2,2)), ...
         'FontSize', 10, 'Color', colors(i), 'HorizontalAlignment', 'center', ...
         'BackgroundColor', 'white', 'EdgeColor', colors(i));
end

% 标记三个点
scatter(points(:,1), points(:,2), 100, 'b', 'filled');
text(points(1,1), points(1,2)+0.3, '点1', 'FontSize', 12, 'HorizontalAlignment', 'center');
text(points(2,1), points(2,2)-0.3, '点2', 'FontSize', 12, 'HorizontalAlignment', 'center');
text(points(3,1), points(3,2)-0.3, '点3', 'FontSize', 12, 'HorizontalAlignment', 'center');

% 绘制从中心到顶点的连线
for i = 1:3
    plot([center_x, points(i,1)], [center_y, points(i,2)], 'g--', 'LineWidth', 1);
end

% 设置坐标轴
xlim([x_range(1)-1, x_range(2)+1]);
ylim([y_range(1)-1, y_range(2)+1]);
xlabel('X轴');
ylabel('Y轴');
title(sprintf('等边三角形与半径为2的圆覆盖 (旋转角度: %.1f°)', random_angle));

% 计算覆盖率和重叠情况
fprintf('=== 覆盖分析 ===\n');
fprintf('顶点到中心距离: %.2f\n', center_distance);
fprintf('随机旋转角度: %.2f°\n', random_angle);
fprintf('圆心坐标:\n');
for i = 1:3
    fprintf('  点%d: (%.2f, %.2f)\n', i, points(i,1), points(i,2));
end

% 验证等边三角形
dist12 = sqrt((x1-x2)^2 + (y1-y2)^2);
dist23 = sqrt((x2-x3)^2 + (y2-y3)^2);
dist31 = sqrt((x3-x1)^2 + (y3-y1)^2);
fprintf('\n=== 等边三角形验证 ===\n');
fprintf('边1-2长度: %.4f\n', dist12);
fprintf('边2-3长度: %.4f\n', dist23);
fprintf('边3-1长度: %.4f\n', dist31);
fprintf('最大边长差: %.4f\n', max([abs(dist12-dist23), abs(dist23-dist31), abs(dist31-dist12)]));

% 检查圆是否重叠
fprintf('\n=== 重叠检查 ===\n');
overlap_found = false;
for i = 1:2
    for j = i+1:3
        distance = sqrt((points(i,1)-points(j,1))^2 + (points(i,2)-points(j,2))^2);
        if distance < 2 * radius
            fprintf('圆%d和圆%d重叠! 圆心距离: %.2f < 直径: %.2f\n', i, j, distance, 2*radius);
            overlap_found = true;
        else
            fprintf('圆%d和圆%d不重叠。圆心距离: %.2f >= 直径: %.2f\n', i, j, distance, 2*radius);
        end
    end
end

if ~overlap_found
    fprintf('所有圆均不重叠！\n');
end

hold off;

% 绘制覆盖区域示意图
figure('Position', [950, 100, 800, 800]);
hold on;
grid on;
axis equal;

% 绘制坐标系和圆
rectangle('Position', [x_range(1), y_range(1), diff(x_range), diff(y_range)], ...
          'EdgeColor', 'k', 'LineWidth', 2, 'LineStyle', '--');

% 绘制覆盖区域网格
[x_grid, y_grid] = meshgrid(x_range(1):0.5:x_range(2), y_range(1):0.5:y_range(2));
covered_points = zeros(size(x_grid));

% 检查每个网格点是否被覆盖
for i = 1:size(x_grid,1)
    for j = 1:size(x_grid,2)
        for k = 1:3
            distance = sqrt((x_grid(i,j)-points(k,1))^2 + (y_grid(i,j)-points(k,2))^2);
            if distance <= radius
                covered_points(i,j) = 1;
                break;
            end
        end
    end
end

% 绘制覆盖区域
scatter(x_grid(covered_points==1), y_grid(covered_points==1), 20, 'g', 'filled');
scatter(x_grid(covered_points==0), y_grid(covered_points==0), 20, 'r', 'filled');

% 绘制圆边界
for i = 1:3
    x_circle = points(i,1) + radius * cos(theta);
    y_circle = points(i,2) + radius * sin(theta);
    plot(x_circle, y_circle, 'b-', 'LineWidth', 2);
end

% 绘制三角形和中心点
plot([x1, x2, x3, x1], [y1, y2, y3, y1], 'k-', 'LineWidth', 2);
plot(center_x, center_y, 'ko', 'MarkerSize', 8, 'MarkerFaceColor', 'k');

% 计算覆盖率
total_points = numel(x_grid);
covered_count = sum(covered_points(:));
coverage_rate = covered_count / total_points * 100;

xlim([x_range(1)-1, x_range(2)+1]);
ylim([y_range(1)-1, y_range(2)+1]);
xlabel('X轴');
ylabel('Y轴');
title(sprintf('覆盖区域可视化 (覆盖率: %.1f%%)', coverage_rate));
legend('覆盖区域', '未覆盖区域', '圆边界', '等边三角形', '中心点', 'Location', 'best');

hold off;

fprintf('\n=== 覆盖统计 ===\n');
fprintf('总网格点数: %d\n', total_points);
fprintf('覆盖网格点数: %d\n', covered_count);
fprintf('覆盖率: %.2f%%\n', coverage_rate);

% 输出直径信息
fprintf('\n=== 随机直径信息 ===\n');
for i = 1:3
    endpoints = diameter_endpoints{i};
    fprintf('圆%d - 直径角度: %.1f°\n', i, diameter_angles(i));
    fprintf('  端点1: (%.3f, %.3f)\n', endpoints(1,1), endpoints(1,2));
    fprintf('  端点2: (%.3f, %.3f)\n', endpoints(2,1), endpoints(2,2));
    
    % 验证直径长度
    diam_length = sqrt((endpoints(1,1)-endpoints(2,1))^2 + (endpoints(1,2)-endpoints(2,2))^2);
    fprintf('  直径长度: %.3f (理论值: %.3f)\n', diam_length, 2*radius);
end



fprintf('\n程序执行完成！\n');